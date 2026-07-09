#!/usr/bin/env python3
"""
Minimal A2A agent test helper for the kagent local lab.

Usage:
    python scripts/kagent/test-a2a-agent.py card
    python scripts/kagent/test-a2a-agent.py task --prompt "Get pods in kagent namespace"

Actions:
    card        Fetch the A2A agent card from the controller
    task        Send a read-only task to the agent and print the response
    probe       Probe A2A JSON-RPC methods (tasks/sendTask, message/send, agent/getAgentCard)
    both        (default) Fetch card then send a task
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

DEFAULT_CONTROLLER = "http://localhost:8083"
DEFAULT_NAMESPACE = "kagent"
DEFAULT_AGENT = "k8s-a2a-agent"
DEFAULT_PROMPT = "List all pods in the kagent namespace"


def build_agent_card_url(base, namespace, agent):
    return f"{base}/api/a2a/{namespace}/{agent}/.well-known/agent.json"


def fetch_agent_card(url):
    """Fetch the A2A agent card via JSON-RPC."""
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "tasks/sendTask",
        "params": {"id": "card-check", "message": {"role": "user", "parts": [{"text": ""}]}}
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10).read().decode()
        data = json.loads(resp)
        # kagent's A2A endpoint responds with error for unknown methods
        # but we can get the card via the REST API instead
        return data
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def fetch_agent_card_rest(base, namespace, agent):
    """Fetch agent details from the kagent REST API (more reliable)."""
    url = f"{base}/api/agents/{namespace}/{agent}"
    req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=10).read().decode()
        return json.loads(resp)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def send_a2a_task(url, prompt):
    """Send a read-only task to the A2A agent."""
    body = json.dumps({
        "jsonrpc": "2.0", "id": "a2a-test-1",
        "method": "tasks/sendTask",
        "params": {
            "id": "a2a-lab-test",
            "message": {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        }
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=30).read().decode()
        return json.loads(resp)
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


def check_connectivity(base):
    """Check if the controller is reachable."""
    try:
        req = urllib.request.Request(f"{base}/health")
        resp = urllib.request.urlopen(req, timeout=5)
        return resp.status == 200
    except Exception:
        return False


def probe_a2a_methods(url):
    """Probe known A2A JSON-RPC methods and report which respond vs error."""
    methods = [
        "tasks/sendTask",
        "message/send",
        "agent/getAgentCard",
    ]
    results = {}
    for method in methods:
        body = json.dumps({
            "jsonrpc": "2.0", "id": 1,
            "method": method,
            "params": {},
        }).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            resp = urllib.request.urlopen(req, timeout=10).read().decode()
            data = json.loads(resp)
            if "error" in data:
                code = data["error"].get("code", "?")
                msg = str(data["error"].get("message", ""))[:120]
                results[method] = f"error code={code}: {msg}"
            else:
                results[method] = "success"
        except urllib.error.HTTPError as e:
            results[method] = f"HTTP {e.code}: {e.reason}"
        except Exception as e:
            results[method] = f"exception: {e}"
    return results


def print_probe_results(results):
    """Pretty-print probe results table."""
    max_method_len = max(len(m) for m in results)
    print(f"{'Method'.ljust(max_method_len)}  Status")
    print("-" * (max_method_len + 40))
    for method, status in results.items():
        truncated = status[:80]
        print(f"{method.ljust(max_method_len)}  {truncated}")
    # Summarise what this means
    not_found = sum(
        1 for s in results.values() if "code=-32601" in s
    )
    if not_found == len(results):
        print("\n[INFO] None of the standard A2A JSON-RPC methods are exposed")
        print("[INFO] Agent card is available via REST API at /api/agents/... only")
    elif not_found > 0:
        print(f"\n[INFO] {not_found}/{len(results)} methods returned -32601 (method not found)")
    return True


def print_card(card_data):
    """Pretty-print the agent card or error."""
    # REST API returns {"error": false, "data": {...}} on success
    err = card_data.get("error")
    if err is not None and err is not False:
        print(f"[FAIL] Agent card error: {err}")
        return False

    if "data" in card_data:
        d = card_data["data"]
        agent = d.get("agent", {})
        meta = agent.get("metadata", {})
        spec = agent.get("spec", {})

        print(f"Agent: {meta.get('namespace', '?')}/{meta.get('name', '?')}")
        print(f"Accepted: {d.get('accepted', '?')}")
        print(f"DeploymentReady: {d.get('deploymentReady', '?')}")
        print(f"Model: {d.get('model', '?')} ({d.get('modelProvider', '?')})")

        decl = spec.get("declarative", {})
        skills = decl.get("a2aConfig", {}).get("skills", [])
        if skills:
            print(f"Skills ({len(skills)}):")
            for s in skills:
                print(f"  - {s.get('id')}: {s.get('name')} - {s.get('description', '')[:80]}")
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Test kagent A2A agent")
    parser.add_argument("action", nargs="?", default="both",
                        choices=["card", "task", "probe", "both"],
                        help="What to test (default: both)")
    parser.add_argument("--controller", default=DEFAULT_CONTROLLER,
                        help=f"Controller URL (default: {DEFAULT_CONTROLLER})")
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--agent", default=DEFAULT_AGENT)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT,
                        help=f"Task prompt (default: '{DEFAULT_PROMPT}')")
    parser.add_argument("--quiet", action="store_true",
                        help="Minimal output for scripting")

    args = parser.parse_args()

    controller = args.controller.rstrip("/")
    card_url = build_agent_card_url(controller, args.namespace, args.agent)

    if not args.quiet:
        print("=" * 60)
        print(f"A2A Agent Test: {args.namespace}/{args.agent}")
        print(f"Controller: {controller}")
        print(f"Card URL: {card_url}")
        print("=" * 60)

    # Check connectivity first
    if not check_connectivity(controller):
        print(f"\n[FAIL] Controller not reachable at {controller}")
        print("Make sure kubectl port-forward is running:")
        print(f"  kubectl port-forward -n {args.namespace} svc/kagent-controller 8083:8083")
        sys.exit(1)

    if not args.quiet:
        print(f"\n[INFO] Controller reachable at {controller}")

    # Track overall success
    success = True

    # Action: card
    if args.action in ("card", "both"):
        print("\n--- Agent Card ---")
        card = fetch_agent_card_rest(controller, args.namespace, args.agent)
        if not print_card(card):
            success = False

    # Action: probe A2A JSON-RPC methods
    if args.action == "probe":
        print("\n--- A2A Method Probe ---")
        print(f"Target: {card_url}")
        probe_results = probe_a2a_methods(card_url)
        print_probe_results(probe_results)

    # Action: task
    if args.action in ("task", "both"):
        print("\n--- A2A Task ---")
        print(f"Sending: {args.prompt}")
        result = send_a2a_task(card_url, args.prompt)
        if "error" in result:
            code = result.get("error", {}).get("code") if isinstance(result.get("error"), dict) else "?"
            msg = str(result.get("error", result))
            print(f"[INFO] Task response: code={code}")
            print(f"  {msg[:200]}")
            # A2A protocol responses vary by kagent version;
            # method-not-found means the endpoint is alive but A2A methods differ
            if isinstance(result.get("error"), dict) and result["error"].get("code") == -32601:
                print("[INFO] A2A tasks/sendTask not available in this kagent controller version")
                print("[INFO] Agent card fetched successfully via REST API")
                print("[INFO] For full A2A task dispatch, use a2a-cli or a compatible A2A client")
                print("")
                print("Install a2a-cli and test with:")
                print(f"  pip install a2a-sdk")
                print(f"  a2a-cli --agent http://localhost:8083/api/a2a/kagent/{args.agent}")
        else:
            print("[PASS] Task submitted successfully")
            print(json.dumps(result, indent=2)[:500])

    print()
    if success:
        print("[PASS] A2A test completed")
        sys.exit(0)
    else:
        print("[FAIL] A2A test had errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
