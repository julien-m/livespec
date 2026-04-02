interface AuthResult {
  success: boolean;
  token?: string;
  error?: string;
}

export async function login(email: string, password: string): Promise<AuthResult> {
  if (!email || !password) {
    return { success: false, error: "Email and password are required" };
  }
  return { success: true, token: `tok_${Date.now()}` };
}

export async function logout(): Promise<void> {
  // Invalidate session on server side
  return;
}
