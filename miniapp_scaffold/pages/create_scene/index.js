const { uploadImage } = require('../../services/upload');
const { createTask } = require('../../services/task');
const { saveRecentTask } = require('../../utils/scene-storage');

Page({
  data: {
    imagePath: '',
    uploading: false,
    errorMessage: ''
  },

  async chooseImage() {
    try {
      const result = await new Promise((resolve, reject) => {
        wx.chooseMedia({
          count: 1,
          mediaType: ['image'],
          sourceType: ['album', 'camera'],
          success: resolve,
          fail: reject
        });
      });
      const file = result.tempFiles && result.tempFiles[0];
      this.setData({
        imagePath: file ? file.tempFilePath : '',
        errorMessage: ''
      });
    } catch (error) {
      this.setData({ errorMessage: '选择图片失败' });
    }
  },

  async submitTask() {
    if (!this.data.imagePath) {
      this.setData({ errorMessage: '请先选择图片' });
      return;
    }

    this.setData({ uploading: true, errorMessage: '' });
    try {
      const uploadResult = await uploadImage(this.data.imagePath);
      const task = await createTask({
        jobType: 'generate_private_scene',
        sourceImagePath: uploadResult.localPath,
        sceneTitle: null,
        sceneHint: null
      });
      saveRecentTask(task);
      this.setData({ uploading: false });
      wx.navigateTo({ url: `/pages/task_center/index?jobId=${task.jobId}` });
    } catch (error) {
      this.setData({ uploading: false, errorMessage: error.message || '创建任务失败' });
    }
  }
});
