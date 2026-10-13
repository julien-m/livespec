"""Risk-proportional delivery: QE-driven lane and one end-of-feature review (feature 086).

The lane is decided by the CLI from the reviewed QE classification, never from an
agent's declaration; the end-of-feature review is recorded against hashed file
identities of the complete feature diff so it cannot silently cover a partial diff.
"""
