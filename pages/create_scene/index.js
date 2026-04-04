const { uploadImage } = require('../../services/upload');
const { createSceneTask, getSceneTask } = require('../../services/task');

const POLL_INTERVAL_MS = 2000;

Page({
  data: {
    imagePath: '',
    sceneTitle: '',
    includeVerbs: true,
    submitting: false,
    stage: 'idle',
    uploadId: '',
    taskId: '',
    taskStatus: '',
    taskStep: '',
    taskProgress: 0,
    sceneId: '',
    errorMessage: ''
  },

  onUnload() {
    this.stopPolling();
  },

  chooseFromCamera() {
    this.chooseImage(['camera']);
  },

  chooseFromAlbum() {
    this.chooseImage(['album']);
  },

  chooseImage(sourceType) {
    wx.chooseMedia({
      count: 1,
      mediaType: ['image'],
      sourceType,
      success: (result) => {
        const file = result.tempFiles && result.tempFiles[0];
        this.stopPolling();
        this.setData({
          imagePath: file ? file.tempFilePath : '',
          uploadId: '',
          taskId: '',
          taskStatus: '',
          taskStep: '',
          taskProgress: 0,
          sceneId: '',
          stage: 'idle',
          errorMessage: ''
        });
      },
      fail: (error) => {
        if (error && error.errMsg && error.errMsg.indexOf('cancel') >= 0) {
          return;
        }
        this.setData({
          errorMessage: '选择图片失败'
        });
      }
    });
  },

  onTitleInput(event) {
    this.setData({
      sceneTitle: event.detail.value || ''
    });
  },

  onToggleVerbs(event) {
    this.setData({
      includeVerbs: !!event.detail.value
    });
  },

  async onSubmit() {
    if (!this.data.imagePath) {
      this.setData({
        errorMessage: '请先拍照或上传图片'
      });
      return;
    }

    this.stopPolling();
    this.setData({
      submitting: true,
      stage: 'uploading',
      errorMessage: '',
      taskProgress: 5
    });

    try {
      const uploadResult = await uploadImage(this.data.imagePath);
      this.setData({
        uploadId: uploadResult.uploadId || '',
        stage: 'creating',
        taskProgress: 15
      });

      const task = await createSceneTask({
        uploadId: uploadResult.uploadId,
        title: (this.data.sceneTitle || '').trim(),
        includeVerbs: this.data.includeVerbs,
        accent: 'en-US',
        voiceGender: 'female',
        voiceName: 'JennyNeural'
      });

      this.setData({
        taskId: task.taskId || '',
        taskStatus: task.status || 'queued',
        stage: 'polling',
        submitting: false,
        taskProgress: 20
      });
      this.startPolling();
    } catch (error) {
      this.setData({
        submitting: false,
        stage: 'failed',
        errorMessage: error.message || '提交生成任务失败'
      });
    }
  },

  startPolling() {
    if (!this.data.taskId) {
      return;
    }
    this.stopPolling();
    this.pollTask();
    this.pollTimer = setInterval(() => {
      this.pollTask();
    }, POLL_INTERVAL_MS);
  },

  stopPolling() {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  },

  async pollTask() {
    if (!this.data.taskId) {
      return;
    }

    try {
      const task = await getSceneTask(this.data.taskId);
      const nextStage = task.status === 'done' ? 'done' : task.status === 'failed' ? 'failed' : 'polling';
      this.setData({
        taskStatus: task.status || '',
        taskStep: task.step || '',
        taskProgress: typeof task.progress === 'number' ? task.progress : this.data.taskProgress,
        sceneId: task.sceneId || '',
        stage: nextStage,
        errorMessage: task.status === 'failed' ? (task.errorMessage || '场景生成失败') : ''
      });

      if (task.status === 'done') {
        this.stopPolling();
        wx.showToast({
          title: '场景已生成',
          icon: 'success',
          duration: 1200
        });
      }

      if (task.status === 'failed') {
        this.stopPolling();
      }
    } catch (error) {
      this.stopPolling();
      this.setData({
        stage: 'failed',
        errorMessage: error.message || '任务状态获取失败'
      });
    }
  },

  onOpenScene() {
    if (!this.data.sceneId) {
      return;
    }
    wx.navigateTo({
      url: `/pages/scene_runtime/index?sceneId=${this.data.sceneId}`
    });
  },

  onOpenMyScenes() {
    wx.navigateTo({
      url: '/pages/my_scenes/index'
    });
  }
});
