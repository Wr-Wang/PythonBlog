import client from "./http.js";

export function listWorkflowTasks(params = {}) {
  return client.get("/admin/workflow/tasks", { params });
}

export function batchWorkflowAction(payload) {
  return client.post("/admin/workflow/tasks/batch-action", payload);
}

export function listWorkflowReasonTemplates() {
  return client.get("/admin/workflow/reason-templates");
}

export function listWorkflowTaskAudits(taskId) {
  return client.get(`/admin/workflow/tasks/${encodeURIComponent(taskId)}/audits`);
}

export function getWorkflowSlaSummary(params = {}) {
  return client.get("/admin/workflow/sla-summary", { params });
}
