/** Instrument direct await/return in inline, unshadowed Vitest test callbacks. */
import { randomUUID } from "node:crypto";
import type { Node, Program } from "estree";
import type MagicString from "magic-string";

type RangedNode = Node & { start: number; end: number };
type Editor = typeof MagicString;
type Parser = (code: string, options?: { jsx?: boolean }) => Program;
const TEST_IMPORTS = new Set(["test", "it"]);

const children = (node: Node): Node[] =>
	Object.values(node).flatMap((value: unknown) => {
		const values: unknown[] = Array.isArray(value) ? value : [value];
		// The parser owns these nodes; select only its typed AST children, never arbitrary source values.
		return values.filter((child): child is Node =>
			Boolean(child && typeof child === "object" && "type" in child),
		);
	});

const bindingNames = (node: Node): string[] => {
	if (node.type === "Identifier") return [node.name];
	return children(node).flatMap(bindingNames);
};

const imports = (program: Program): Set<string> => {
	const names = new Set<string>();
	for (const statement of program.body) {
		if (
			statement.type !== "ImportDeclaration" ||
			statement.source.value !== "vitest"
		)
			continue;
		for (const specifier of statement.specifiers) {
			if (
				specifier.type === "ImportSpecifier" &&
				specifier.imported.type === "Identifier" &&
				TEST_IMPORTS.has(specifier.imported.name)
			)
				names.add(specifier.local.name);
		}
	}
	const visit = (node: Node): void => {
		// Any shadow anywhere conservatively disables that binding for this module.
		if (node.type === "VariableDeclarator")
			for (const name of bindingNames(node.id)) names.delete(name);
		if (
			node.type === "FunctionDeclaration" ||
			node.type === "FunctionExpression" ||
			node.type === "ArrowFunctionExpression"
		) {
			if (node.type !== "ArrowFunctionExpression" && node.id)
				names.delete(node.id.name);
			for (const parameter of node.params)
				for (const name of bindingNames(parameter)) names.delete(name);
		}
		if (
			(node.type === "ClassDeclaration" || node.type === "ClassExpression") &&
			node.id
		)
			names.delete(node.id.name);
		if (node.type === "CatchClause" && node.param)
			for (const name of bindingNames(node.param)) names.delete(name);
		for (const child of children(node)) visit(child);
	};
	visit(program);
	return names;
};

const isDirectMatcher = (node: Node): boolean => {
	if (
		node.type !== "CallExpression" ||
		node.callee.type !== "MemberExpression" ||
		node.callee.computed
	)
		return false;
	let receiver: Node = node.callee.object;
	let hasAsyncForm = false;
	while (receiver.type === "MemberExpression") {
		if (receiver.computed || receiver.property.type !== "Identifier")
			return false;
		const name = receiver.property.name;
		if (!["not", "resolves", "rejects"].includes(name)) return false;
		hasAsyncForm ||= name === "resolves" || name === "rejects";
		receiver = receiver.object;
	}
	return hasAsyncForm && receiver.type === "CallExpression";
};

const isTestCallback = (
	node: Node,
	parent: Node | undefined,
	names: Set<string>,
): boolean =>
	Boolean(
		parent?.type === "CallExpression" &&
			parent.arguments[1] === node &&
			parent.arguments[0]?.type === "Literal" &&
			typeof parent.arguments[0].value === "string" &&
			parent.callee.type === "Identifier" &&
			names.has(parent.callee.name),
	);

/** Wrap only direct execution syntax; unknown registrations and Promise compositions stay unsupported. */
export const instrumentAsyncConsumption = (
	code: string,
	id: string,
	parse: Parser,
	StringEditor: Editor,
	helper: string,
): { code: string; map: ReturnType<MagicString["generateMap"]> } | null => {
	const program = parse(code, { jsx: true });
	const names = imports(program);
	if (!names.size) return null;
	const editor = new StringEditor(code);
	const alias = `__livespecAwait_${randomUUID().replaceAll("-", "")}`;
	const spans = new Set<string>();
	const wrap = (node: Node): void => {
		if (!isDirectMatcher(node)) return;
		// Rollup parser ranges address exactly the post-transform JavaScript being instrumented.
		const range = node as RangedNode;
		const span = `${range.start}:${range.end}`;
		if (spans.has(span)) return;
		spans.add(span);
		editor.appendLeft(range.start, `${alias}(`);
		editor.appendRight(range.end, ")");
	};
	const visit = (
		node: Node,
		parent: Node | undefined,
		active: boolean,
		allowReturn: boolean,
	): void => {
		if (
			node.type === "FunctionDeclaration" ||
			node.type === "FunctionExpression" ||
			node.type === "ArrowFunctionExpression"
		) {
			active = isTestCallback(node, parent, names);
			allowReturn = true;
			if (active && node.type === "ArrowFunctionExpression" && node.expression)
				wrap(node.body);
		}
		// A finally may replace a return's completion; refuse all such return sites conservatively.
		if (node.type === "TryStatement" && node.finalizer) allowReturn = false;
		if (active && node.type === "AwaitExpression") wrap(node.argument);
		if (
			active &&
			allowReturn &&
			node.type === "ReturnStatement" &&
			node.argument
		)
			wrap(node.argument);
		for (const child of children(node)) visit(child, node, active, allowReturn);
	};
	visit(program, undefined, false, true);
	if (!spans.size) return null;
	// Vite composes this high-resolution edit map with the preceding TS transform's original-source map.
	editor.prepend(
		`import { markAsyncConsumption as ${alias} } from ${JSON.stringify(helper)};\n`,
	);
	return {
		code: editor.toString(),
		map: editor.generateMap({ source: id, includeContent: true, hires: true }),
	};
};
