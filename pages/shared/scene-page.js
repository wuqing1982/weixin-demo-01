const { getSceneNeighbors } = require('./scene-registry');

const SWIPE_DISTANCE = 70;
const SWIPE_VERTICAL_TOLERANCE = 80;

function findEntryById(entries, id) {
  return (entries || []).find((entry) => entry.id === id) || null;
}

function normalizeEntry(entry) {
  if (!entry) {
    return null;
  }

  return Object.assign({}, entry, {
    sentenceTranslation: entry.sentenceTranslation || entry.sentence_translation || ''
  });
}

function createScenePage(sceneData) {
  const { prevScene, nextScene, sceneTabs } = getSceneNeighbors(sceneData.sceneId);
  const normalizedItems = (sceneData.items || []).map(normalizeEntry);
  const normalizedVerbs = (sceneData.verbs || []).map(normalizeEntry);

  return {
    data: {
      sceneId: sceneData.sceneId,
      title: sceneData.title,
      background: sceneData.background,
      items: normalizedItems,
      verbs: normalizedVerbs,
      activeId: '',
      activeType: '',
      activeEntry: null,
      prevScene,
      nextScene,
      sceneTabs,
      // 工具栏状态
      deviceMode: 'mobile', // mobile | tablet | desktop
      playbackRate: 1.0,
      isLooping: false
    },

    onLoad() {
      wx.setNavigationBarTitle({
        title: sceneData.title
      });

      this.audioContext = wx.createInnerAudioContext();
      this.audioContext.obeyMuteSwitch = false;
      this.audioContext.onError(() => {
        wx.showToast({
          title: '音频播放失败',
          icon: 'none'
        });
      });

      // 尝试从本地存储读取播放速度
      try {
        const savedRate = wx.getStorageSync('preferredPlaybackRate');
        if (savedRate) {
          this.setData({
            playbackRate: parseFloat(savedRate) || 1.0
          });
        }
      } catch (e) {
        console.log('读取播放速度失败');
      }
    },

    onHide() {
      this.stopAudio();
    },

    onUnload() {
      this.destroyAudio();
    },

    onTouchStart(event) {
      const touch = event.changedTouches && event.changedTouches[0];
      if (!touch) {
        return;
      }

      this.touchStartPoint = {
        x: touch.pageX,
        y: touch.pageY
      };
    },

    onTouchEnd(event) {
      const touch = event.changedTouches && event.changedTouches[0];
      const start = this.touchStartPoint;

      this.touchStartPoint = null;

      if (!touch || !start) {
        return;
      }

      const deltaX = touch.pageX - start.x;
      const deltaY = touch.pageY - start.y;

      if (Math.abs(deltaY) > SWIPE_VERTICAL_TOLERANCE || Math.abs(deltaX) < SWIPE_DISTANCE) {
        return;
      }

      if (deltaX < 0) {
        this.navigateToScene(this.data.nextScene);
        return;
      }

      this.navigateToScene(this.data.prevScene);
    },

    onTapHotspot(event) {
      const { id } = event.currentTarget.dataset;
      const item = findEntryById(this.data.items, id);

      if (!item) {
        return;
      }

      this.activateEntry(item, 'item');
    },

    onTapVerb(event) {
      const { id } = event.currentTarget.dataset;
      const verb = findEntryById(this.data.verbs, id);

      if (!verb) {
        return;
      }

      this.activateEntry(verb, 'verb');
    },

    onCloseOverlay() {
      this.stopAudio();
      this.setData({
        activeId: '',
        activeType: '',
        activeEntry: null
      });
    },

    onTapPrevScene() {
      this.navigateToScene(this.data.prevScene);
    },

    onTapNextScene() {
      this.navigateToScene(this.data.nextScene);
    },

    onTapScenePill(event) {
      const { sceneId } = event.currentTarget.dataset;
      const targetScene = this.data.sceneTabs.find((item) => item.sceneId === sceneId);
      this.navigateToScene(targetScene);
    },

    // ========== 工具栏功能 ==========
    
    // 切换设备模式
    onSwitchDevice(event) {
      const { mode } = event.currentTarget.dataset;
      this.setData({
        deviceMode: mode
      });
      wx.showToast({
        title: mode === 'mobile' ? '手机视图' : mode === 'tablet' ? '平板视图' : '电脑视图',
        icon: 'none',
        duration: 1000
      });
    },

    // 语速滑块变化
    onRateChange(event) {
      const rate = parseFloat(event.detail.value);
      this.setData({
        playbackRate: rate
      });
      // 保存到本地存储
      try {
        wx.setStorageSync('preferredPlaybackRate', rate.toString());
      } catch (e) {
        console.log('保存播放速度失败');
      }
    },

    // 语速预设按钮
    onRatePreset(event) {
      const { rate } = event.currentTarget.dataset;
      const rateValue = parseFloat(rate);
      this.setData({
        playbackRate: rateValue
      });
      // 保存到本地存储
      try {
        wx.setStorageSync('preferredPlaybackRate', rate);
      } catch (e) {
        console.log('保存播放速度失败');
      }
      wx.showToast({
        title: rateValue < 1 ? '慢速播放' : '快速播放',
        icon: 'none',
        duration: 800
      });
    },

    // 切换循环播放
    onToggleLoop() {
      const newLoopState = !this.data.isLooping;
      this.setData({
        isLooping: newLoopState
      });
      wx.showToast({
        title: newLoopState ? '循环播放已开启' : '循环播放已关闭',
        icon: 'none',
        duration: 1200
      });
    },

    // 打开摄像头（占位功能）
    onOpenCamera() {
      wx.showModal({
        title: '📷 摄像头',
        content: '摄像头功能开发中...\n\n将支持：\n• 拍照学习\n• AR 场景互动\n• 实时识别',
        showCancel: false,
        confirmText: '知道了'
      });
    },

    // 导出视频（占位功能）
    onExportVideo() {
      wx.showModal({
        title: '🎬 导出视频',
        content: '视频导出功能开发中...\n\n将支持：\n• 场景学习记录导出\n• 带配音的视频生成\n• 分享到朋友圈',
        showCancel: false,
        confirmText: '知道了'
      });
    },

    // ========== 核心功能 ==========

    activateEntry(entry, type) {
      this.setData({
        activeId: entry.id,
        activeType: type,
        activeEntry: entry
      });

      this.playAudio(entry);
    },

    navigateToScene(scene) {
      if (!scene || !scene.route || scene.sceneId === this.data.sceneId) {
        return;
      }

      this.stopAudio();
      wx.redirectTo({
        url: scene.route
      });
    },

    playAudio(entry) {
      if (!this.audioContext || !entry.audio) {
        // 如果没有音频文件，使用 TTS 或显示提示
        wx.showToast({
          title: '使用在线语音...',
          icon: 'none',
          duration: 1000
        });
        this.simulateTTS(entry);
        return;
      }

      // 设置播放速度
      this.audioContext.playbackRate = this.data.playbackRate;
      this.audioContext.stop();
      this.audioContext.src = entry.audio;
      this.audioContext.play();

      // 如果开启了循环播放，监听播放结束
      if (this.data.isLooping) {
        this.audioContext.onEnded(() => {
          if (this.data.isLooping && this.data.activeId === entry.id) {
            setTimeout(() => {
              this.audioContext.play();
            }, 500);
          }
        });
      }
    },

    // 模拟 TTS 功能（当没有预录音频时使用）
    simulateTTS(entry) {
      // 这里可以集成微信的 TTS 或其他语音服务
      console.log('TTS:', entry.word, entry.sentence);
    },

    stopAudio() {
      if (this.audioContext) {
        this.audioContext.stop();
      }
    },

    destroyAudio() {
      if (this.audioContext) {
        this.audioContext.destroy();
        this.audioContext = null;
      }
    }
  };
}

module.exports = {
  createScenePage
};
