# Security

This is a public static site. Do not add credentials or private personal data to
HTML, JSON, JavaScript, PDFs or deployment output: browser-delivered data is public.

Do not include secret values or exploit details in public issues or pull requests.
Use GitHub's private vulnerability reporting **if enabled**; otherwise establish a
private channel with the repository owner before sharing sensitive information.
No dedicated security mailbox or response-time commitment is configured here.

If a credential is exposed, its owner must revoke/rotate it. Removing a tracked
value does not remove historical exposure. Do not rewrite shared history without
owner authorization.

Local controls: generated hash-based CSP, self-hosted runtime, restricted framing,
`nosniff`, permissions policy, package allowlist/symlink rejection, pinned CI tools,
and an offline high-confidence secret-pattern check. These do not replace a full
security review or provider-side settings. `tools/serve.py` makes an explicitly
local-only framing exception for previews; deployed `_headers` remains strict.
