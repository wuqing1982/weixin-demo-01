Page({
  data: {
    actions: [
      { id: 'library', title: '公开场景库', desc: '浏览会员可见的英语学习场景', url: '/pages/library/index' },
      { id: 'create', title: '创建私人场景', desc: '上传照片并创建专属场景', url: '/pages/create_scene/index' },
      { id: 'tasks', title: '任务中心', desc: '查看生成进度和结果', url: '/pages/task_center/index' },
      { id: 'mine', title: '我的场景', desc: '查看我生成过的场景', url: '/pages/my_scenes/index' }
    ]
  },

  onOpen(event) {
    wx.navigateTo({ url: event.currentTarget.dataset.url });
  }
});
