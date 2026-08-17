# AI Disclaimer

**Last updated:** 2025-01-01

## AI-Generated Content

aiZee generates, processes, and evaluates content using artificial
intelligence. This includes:

- **Persona Detection:** AI determines which specialized persona best matches
  a user prompt based on keyword matching.
- **Policy Evaluation:** AI evaluates whether actions comply with defined
  rules and budget constraints.
- **Memory Search:** AI performs keyword and vector similarity search over
  ingested documentation.
- **Workflow Execution:** AI orchestrates multi-step workflows with
  policy gates at each step.

## Limitations

### Accuracy

AI-generated outputs are probabilistic and may contain errors. The software
uses deterministic policy evaluation (not LLM-based) for governance decisions,
but persona detection and memory search rely on heuristic and embedding-based
methods that are not guaranteed to be correct.

### Bias

AI systems can reflect biases in their training data. The persona detection
system uses keyword matching which may not account for all contexts or
nuances in user prompts.

### No Autonomous Action

The software does not execute actions autonomously. All actions require
explicit user approval or pass through policy gates that can block, ask
for approval, or allow based on configured rules.

## Best Practices

1. **Review all AI outputs** before acting on them.
2. **Configure policy rules** to match your security requirements.
3. **Set budget limits** to prevent runaway costs.
4. **Regularly audit** the memory store and audit logs.
5. **Use the guardian** to enforce additional safety rules.

## Reporting Issues

If you encounter harmful or incorrect AI outputs, please report them at:
https://github.com/m3taz-ahmed/ai-globals/issues
