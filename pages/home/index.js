Page({
  data: {
    actions: [
      {
        id: 'library',
        title: '公开场景库',
        desc: '从后端加载场景列表，再进入统一 runtime 页面。',
        url: '/pages/library/index'
      },
      {
        id: 'create',
        title: '拍照生成我的场景',
        desc: '上传图片，提交后端任务，轮询生成进度，再打开私人场景。',
        url: '/pages/create_scene/index'
      },
      {
        id: 'mine',
        title: '我的生成场景',
        desc: '查看当前调试用户生成过的私人场景列表。',
        url: '/pages/my_scenes/index'
      },
      {
        id: 'breakfast',
        title: '直接打开早餐场景',
        desc: '跳过列表，直接验证场景详情接口和图片音频加载。',
        url: '/pages/scene_runtime/index?sceneId=scene_breakfast'
      }
    ]
  },

  onOpen(event) {
    wx.navigateTo({
      url: event.currentTarget.dataset.url
    });
  }
});
