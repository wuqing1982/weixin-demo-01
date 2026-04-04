const { getTaskDetail } = require('../../services/task');
const { getRecentTasks } = require('../../utils/scene-storage');

Page({
  data: {
    jobId: '',
    task: null,
    loading: true,
    errorMessage: '',
    recentTasks: []
  },

  onLoad(options) {
    this.setData({
      jobId: options.jobId || '',
      recentTasks: getRecentTasks()
    });
  },

  onShow() {
    if (this.data.jobId) {
      this.loadTask(this.data.jobId);
      return;
    }
    this.setData({ loading: false, recentTasks: getRecentTasks() });
  },

  async loadTask(jobId) {
    this.setData({ loading: true, errorMessage: '' });
    try {
      const task = await getTaskDetail(jobId);
      this.setData({ task, loading: false, recentTasks: getRecentTasks() });
      if (task.status === 'running' || task.status === 'queued') {
        clearTimeout(this.pollTimer);
        this.pollTimer = setTimeout(() => this.loadTask(jobId), 3000);
      }
    } catch (error) {
      this.setData({ loading: false, errorMessage: error.message || '任务查询失败' });
    }
  },

  onOpenScene() {
    const sceneId = this.data.task && this.data.task.result && this.data.task.result.sceneId;
    if (sceneId) {
      wx.navigateTo({ url: `/pages/scene_runtime/index?sceneId=${sceneId}` });
    }
  },

  onOpenRecent(event) {
    const jobId = event.currentTarget.dataset.jobId;
    this.setData({ jobId });
    this.loadTask(jobId);
  },

  onUnload() {
    clearTimeout(this.pollTimer);
  }
});
