# Robot Eval Job Request Contract

`robot_eval_job_request.v1` is the shared WebApp-to-Pipeline request boundary for
robot-eval jobs. WebApp may queue, persist, and forward the request; Pipeline
owns scheduling, execution, ranking artifacts, package generation, and proof
closure.

The portable source of truth is the JSON Schema file:

```text
src/blueprint_contracts/schemas/robot_eval_job_request.v1.schema.json
src/blueprint_contracts/schemas/robot_eval_job_request_inbox.v1.schema.json
```

Python consumers should import module-level helpers:

```python
from blueprint_contracts.robot_eval_job_request_contract import (
    ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION,
    robot_eval_job_request_schema,
)
```

Node consumers should import the package export:

```js
import {
  ROBOT_EVAL_JOB_REQUEST_SCHEMA_VERSION,
  robotEvalJobRequestSchema,
} from "@blueprint/contracts/robot-eval-job-request";
```

Contract boundaries:

- `schema_version` is `robot_eval_job_request.v1`.
- `queue_contract` for inbox envelopes is `robot_eval_job_request_inbox.v1`.
- `proof_boundary` fields that could upgrade public or operational claims must
  remain `false` in the WebApp-authored request.
- `execution_request.webapp_role` is `queue_and_forward_only`.
- `execution_request.scheduler_owner` is `BlueprintCapturePipeline`.
- `execution_request.artifact_contract` names the Pipeline-owned outputs and
  keeps ranking, startup, package, delivery, and simulator-execution claims
  scoped until Pipeline/owner-system proof exists.

The stdlib validator in `robot_eval_job_request_contract.py` is intentionally a
small constant-drift guard. Consumers with JSON Schema validation available
should validate against the packaged schema itself.
