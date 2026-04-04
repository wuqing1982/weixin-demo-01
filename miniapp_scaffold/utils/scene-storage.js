function saveRecentTask(task) {
  const items = wx.getStorageSync('recentTasks') || [];
  const next = [task].concat(items.filter((item) => item.jobId !== task.jobId)).slice(0, 20);
  wx.setStorageSync('recentTasks', next);
}

function getRecentTasks() {
  return wx.getStorageSync('recentTasks') || [];
}

module.exports = {
  saveRecentTask,
  getRecentTasks
};
