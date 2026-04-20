module.exports = {
  apps: [
    {
      name: 'scene-worker',
      script: 'scripts/run_scene_worker.py',
      interpreter: 'python3',
      args: '--daemon --workers 3 --poll 2',
      cwd: __dirname,
      max_restarts: 10,
      restart_delay: 3000,
      watch: false,
      autorestart: true,
      max_memory_restart: '512M',
      env: {
        PYTHONUNBUFFERED: '1',
      },
    },
  ],
};
