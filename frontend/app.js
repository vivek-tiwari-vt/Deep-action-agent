const els = {
  input: document.getElementById('taskInput'),
  type: document.getElementById('taskType'),
  run: document.getElementById('runBtn'),
  events: document.getElementById('events'),
  status: document.getElementById('status'),
  output: document.getElementById('output'),
};

function log(pre, line) {
  pre.textContent += (typeof line === 'string' ? line : JSON.stringify(line)) + '\n';
  pre.scrollTop = pre.scrollHeight;
}

async function startTask() {
  const body = {
    task_description: els.input.value || 'List three recent AI topics and summarize',
    // Let backend auto-route sub-agents via planner-executor
    task_type: 'mixed',
    priority: 'normal',
    timeout_minutes: 10,
    verbose: false,
  };
  const res = await fetch('/execute', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const txt = await res.text();
    log(els.status, `Error ${res.status}: ${txt}`);
    return;
  }
  const data = await res.json();
  if (!data || !data.task_id) {
    log(els.status, `Bad response: ${JSON.stringify(data)}`);
    return;
  }
  log(els.status, `Queued: ${data.task_id}`);
  streamEvents(data.task_id);
  trackStatus(data.task_id);
}

function streamEvents(taskId) {
  const src = new EventSource(`/events/${taskId}`);
  src.onmessage = (ev) => {
    try {
      const parsed = JSON.parse(ev.data);
      // keep live events concise
      const t = parsed.type || 'event';
      if (t === 'llm_delta' && parsed.data && parsed.data.delta && parsed.data.delta.length > 0) {
        return; // skip token spam
      }
      log(els.events, `[${t}] ${JSON.stringify(parsed)}`);
    } catch {
      log(els.events, ev.data);
    }
  };
  src.onerror = () => {
    log(els.events, 'Event stream closed');
    src.close();
  };
}

async function trackStatus(taskId) {
  let done = false;
  while (!done) {
    await new Promise(r => setTimeout(r, 1500));
    const res = await fetch(`/status/${taskId}`);
    const s = await res.json();
    els.status.textContent = JSON.stringify(s, null, 2);
    if (s.status === 'completed' && s.result && s.result.result) {
      const r = s.result.result;
      if (r.report_path) {
        els.output.textContent = `Report: ${r.report_path}`;
      } else if (typeof r === 'string') {
        els.output.textContent = r;
      } else {
        els.output.textContent = JSON.stringify(r, null, 2);
      }
      done = true;
    }
    if (s.status === 'failed') {
      els.output.textContent = `Failed: ${s.error_message || ''}`;
      done = true;
    }
  }
}

els.run.addEventListener('click', startTask);
