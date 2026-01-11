import time
import uuid
from multiprocessing import Process, Manager
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

DEFAULT_CPUS = 1
DEFAULT_TIME = 5  # seconds

# Shared dictionary for tasks
manager = Manager()
tasks = manager.dict()  # shared across processes


def burn_cpu(duration: int, task_id: str):
    """Busy-loop CPU and mark task done."""
    end = time.time() + duration
    while time.time() < end:
        pass
    # Update task status
    task = tasks[task_id]
    task["status"] = "completed"
    tasks[task_id] = task  # Required for manager.dict() to notice update


def run_load(n_cpus: int, duration: int, task_id: str):
    """Start N CPU burn processes for a task."""
    processes = []
    for _ in range(n_cpus):
        p = Process(target=burn_cpu, args=(duration, task_id))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()


HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>CPU Burner</title>
    <style>
        .task {
            margin-bottom: 10px;
        }
        .bar-container {
            width: 300px;
            height: 20px;
            border: 1px solid #333;
            position: relative;
        }
        .bar {
            height: 100%;
            width: 0%;
            background-color: orange;
            transition: width 0.4s linear;
        }
        .bar.completed {
            background-color: green;
        }
    </style>
</head>
<body>
    <h2>CPU Load Generator</h2>
    <form id="cpuForm">
        <label>CPUs (N):</label>
        <input type="number" name="cpus" id="cpus" value="1" min="1"><br><br>

        <label>Time (seconds, T):</label>
        <input type="number" name="time" id="time" value="5" min="1"><br><br>

        <button type="submit">Execute</button>
    </form>

    <h3>Tasks</h3>
    <div id="tasks"></div>

    <script>
    const form = document.getElementById('cpuForm');
    const tasksDiv = document.getElementById('tasks');

    form.addEventListener('submit', function(event) {
        event.preventDefault(); // Prevent page reload
        const cpus = document.getElementById('cpus').value;
        const time = document.getElementById('time').value;

        fetch('/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `cpus=${cpus}&time=${time}`
        })
        .then(response => response.json())
        .then(data => {
            addTask(data.task_id, data.time_seconds);
        });
    });

    function addTask(task_id, duration) {
        // Create task HTML
        const div = document.createElement('div');
        div.className = 'task';
        div.id = `task-${task_id}`;
        div.innerHTML = `
            <div>Task ${task_id} - Duration: ${duration}s</div>
            <div class="bar-container">
                <div class="bar" id="bar-${task_id}"></div>
            </div>
        `;
        tasksDiv.prepend(div); // Add to top
    }

    function updateTasks() {
        fetch('/status')
        .then(response => response.json())
        .then(data => {
            for (const task_id in data) {
                const task = data[task_id];
                const bar = document.getElementById(`bar-${task_id}`);
                if (!bar) continue;

                let elapsed = Math.min(task.duration, Date.now()/1000 - task.start_time);
                let percent = (elapsed / task.duration) * 100;
                bar.style.width = percent + '%';

                if (task.status === 'completed') {
                    bar.classList.add('completed');
                    bar.style.width = '100%';
                }
            }
        });
    }

    setInterval(updateTasks, 500); // Update every 0.5s
    </script>
</body>
</html>
"""


@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)


@app.route("/execute", methods=["POST", "GET"])
def execute():
    try:
        n_cpus = int(request.values.get("cpus", DEFAULT_CPUS))
        duration = int(request.values.get("time", DEFAULT_TIME))
    except ValueError:
        return jsonify({"error": "Invalid parameters"}), 400

    # Create unique task ID
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "cpus": n_cpus,
        "duration": duration,
        "start_time": time.time(),
        "status": "running"
    }

    # Start background CPU burn process
    p = Process(target=run_load, args=(n_cpus, duration, task_id))
    p.start()

    return jsonify({
        "status": "started",
        "task_id": task_id,
        "cpus_used": n_cpus,
        "time_seconds": duration
    })


@app.route("/status", methods=["GET"])
def status():
    # Return all tasks
    result = {}
    for task_id, task in tasks.items():
        result[task_id] = {
            "cpus": task["cpus"],
            "duration": task["duration"],
            "start_time": task["start_time"],
            "status": task["status"]
        }
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80, threaded=True)
