const { uploadImage } = require('../../services/upload');
const { createSceneTask, getSceneTask } = require('../../services/task');

const POLL_INTERVAL_MS = 2000;
const CANVAS_ID = 'upload-compress-canvas';
const MAX_IMAGE_EDGE = 1600;
const JPG_QUALITY = 0.82;

function getImageInfo(filePath) {
  return new Promise((resolve, reject) => {
    wx.getImageInfo({
      src: filePath,
      success: resolve,
      fail: reject
    });
  });
}

function canvasToTempFilePath(page, options) {
  return new Promise((resolve, reject) => {
    wx.canvasToTempFilePath(
      Object.assign({}, options, {
        canvasId: CANVAS_ID,
        fileType: 'jpg',
        quality: JPG_QUALITY,
        success: resolve,
        fail: reject
      }),
      page
    );
  });
}

function getFileSize(filePath) {
  try {
    const fileSystemManager = wx.getFileSystemManager();
    const stat = fileSystemManager.statSync(filePath);
    return stat && typeof stat.size === 'number' ? stat.size : 0;
  } catch (error) {
    return 0;
  }
}

function formatSize(sizeBytes) {
  if (!sizeBytes) {
    return '';
  }
  if (sizeBytes < 1024) {
    return `${sizeBytes} B`;
  }
  const kb = sizeBytes / 1024;
  if (kb < 1024) {
    return `${kb.toFixed(1)} KB`;
  }
  return `${(kb / 1024).toFixed(2)} MB`;
}

function formatDimensions(width, height) {
  if (!width || !height) {
    return '';
  }
  return `${width} x ${height}`;
}

function formatRatio(sourceSize, optimizedSize) {
  if (!sourceSize || !optimizedSize) {
    return '';
  }
  const savedPercent = ((1 - (optimizedSize / sourceSize)) * 100).toFixed(1);
  return `${savedPercent}%`;
}

function calculateTargetSize(width, height) {
  const longestEdge = Math.max(width, height);
  if (!longestEdge || longestEdge <= MAX_IMAGE_EDGE) {
    return {
      width,
      height
    };
  }

  const scale = MAX_IMAGE_EDGE / longestEdge;
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale))
  };
}

Page({
  data: {
    imagePath: '',
    uploadImagePath: '',
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
    errorMessage: '',
    compressNote: '',
    sourceSizeText: '',
    optimizedSizeText: '',
    sourceDimensionsText: '',
    optimizedDimensionsText: '',
    compressRatioText: '',
    canvasWidth: 1,
    canvasHeight: 1
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
          uploadImagePath: file ? file.tempFilePath : '',
          uploadId: '',
          taskId: '',
          taskStatus: '',
          taskStep: '',
          taskProgress: 0,
          sceneId: '',
          stage: 'idle',
          errorMessage: '',
          compressNote: '',
          sourceSizeText: file ? formatSize(getFileSize(file.tempFilePath)) : '',
          optimizedSizeText: '',
          sourceDimensionsText: '',
          optimizedDimensionsText: '',
          compressRatioText: '',
          canvasWidth: 1,
          canvasHeight: 1
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
      taskProgress: 5,
      compressNote: '正在本地压缩图片并转成 JPG...'
    });

    try {
      const preparedImagePath = await this.prepareUploadImage();
      const uploadResult = await uploadImage(preparedImagePath);
      this.setData({
        uploadId: uploadResult.uploadId || '',
        stage: 'creating',
        taskProgress: 15,
        compressNote: this.data.optimizedSizeText ? `已压缩后上传：${this.data.optimizedSizeText}` : ''
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

  async prepareUploadImage() {
    const sourcePath = this.data.imagePath;
    const sourceSize = getFileSize(sourcePath);
    const imageInfo = await getImageInfo(sourcePath);
    const target = calculateTargetSize(imageInfo.width, imageInfo.height);
    const compressed = await this.compressToJpg(sourcePath, target.width, target.height);
    const optimizedPath = compressed.tempFilePath || sourcePath;
    const optimizedSize = getFileSize(optimizedPath);
    const optimizedInfo = optimizedPath === sourcePath
      ? imageInfo
      : await getImageInfo(optimizedPath);
    const sourceDimensionsText = formatDimensions(imageInfo.width, imageInfo.height);
    const optimizedDimensionsText = formatDimensions(optimizedInfo.width, optimizedInfo.height);
    const compressRatioText = formatRatio(sourceSize, optimizedSize);

    console.log('upload image compression stats', {
      sourcePath,
      optimizedPath,
      sourceSize,
      optimizedSize,
      sourceWidth: imageInfo.width,
      sourceHeight: imageInfo.height,
      optimizedWidth: optimizedInfo.width,
      optimizedHeight: optimizedInfo.height,
      savedPercent: compressRatioText
    });

    this.setData({
      uploadImagePath: optimizedPath,
      sourceSizeText: formatSize(sourceSize),
      optimizedSizeText: formatSize(optimizedSize),
      sourceDimensionsText,
      optimizedDimensionsText,
      compressRatioText,
      compressNote: optimizedPath === sourcePath
        ? '压缩失败，已回退原图上传'
        : `本地已压缩：${formatSize(sourceSize)} -> ${formatSize(optimizedSize)}`
    });

    return optimizedPath;
  },

  async compressToJpg(filePath, targetWidth, targetHeight) {
    try {
      const context = wx.createCanvasContext(CANVAS_ID, this);
      this.setData({
        canvasWidth: targetWidth,
        canvasHeight: targetHeight
      });

      await new Promise((resolve) => {
        setTimeout(resolve, 30);
      });

      context.setFillStyle('#ffffff');
      context.fillRect(0, 0, targetWidth, targetHeight);
      context.drawImage(filePath, 0, 0, targetWidth, targetHeight);

      await new Promise((resolve, reject) => {
        context.draw(false, () => {
          resolve();
        });
        setTimeout(() => {
          reject(new Error('canvas draw timeout'));
        }, 4000);
      });

      return await canvasToTempFilePath(this, {
        x: 0,
        y: 0,
        width: targetWidth,
        height: targetHeight,
        destWidth: targetWidth,
        destHeight: targetHeight
      });
    } catch (error) {
      console.log('compress image failed', error);
      return {
        tempFilePath: filePath
      };
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
