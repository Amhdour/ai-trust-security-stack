package envoy.authz

# Development-only stub policy for Envoy ext_authz.
# Not production-validated.

default allow := false

# Optional kill switch to block all requests in local testing.
kill_switch := object.get(input, "kill_switch", false)

allow if {
  not kill_switch
  method := object.get(input.attributes.request.http, "method", "")
  path := object.get(input.attributes.request.http, "path", "")
  startswith(path, "/api/")
  method in {"GET", "POST"}
}

# Example structured response object often useful for debugging.
result := {
  "allow": allow,
  "reason": reason,
}

reason := "kill switch enabled" if kill_switch
reason := "method/path allowed for local development" if {
  allow
}
reason := "request denied by default policy" if {
  not allow
  not kill_switch
}
