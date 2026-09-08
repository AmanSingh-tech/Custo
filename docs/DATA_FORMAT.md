# Canonical data format

Each JSONL row is one prediction point. Multiple rows may share a `conversation_id`; the split
tool guarantees all such prefixes remain in the same split.

```json
{
  "example_id": "conv-0042:t5",
  "conversation_id": "conv-0042",
  "conversation": [
    {"role": "customer", "text": "My card stopped working."},
    {"role": "agent", "text": "When did this begin?"},
    {"role": "customer", "text": "Yesterday."}
  ],
  "intent": "card_not_working",
  "action": "ask_alternate_terminal_attempted",
  "workflow_state": {"start_time_known": true},
  "policy_version": "policy-0.1.0"
}
```

Required fields are `conversation`, `intent`, and either `action` or `next_action`. Use stable
conversation IDs. Do not split already-generated prefixes independently and do not include future
turns as features.

For ABCD-derived examples, prior system actions are represented as an `agent` turn in the form
`[workflow action completed: action-name]`. It is only appended after the corresponding historical
action, never before the action being predicted, so it preserves the no-future-leakage rule while
making workflow position available to the model.
