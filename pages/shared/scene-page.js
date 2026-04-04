const { getSceneNeighbors } = require('./scene-registry');

const SWIPE_DISTANCE = 70;
const SWIPE_VERTICAL_TOLERANCE = 80;
const DEFAULT_TITLE = '英语场景';

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

function buildNavigation(sceneId, sceneTabs) {
  if (sceneTabs && sceneTabs.length) {
    const index = sceneTabs.findIndex((item) => item.sceneId === sceneId);
    return {
      prevScene: index > 0 ? sceneTabs[index - 1] : null,
      nextScene: index >= 0 && index < sceneTabs.length - 1 ? sceneTabs[index + 1] : null,
      sceneTabs
    };
  }

  if (!sceneId) {
    return {
      prevScene: null,
      nextScene: null,
      sceneTabs: []
    };
  }

  return getSceneNeighbors(sceneId);
}

function buildSceneState(sceneData) {
  const safeSceneData = sceneData || {};
  const navigation = buildNavigation(safeSceneData.sceneId || '', safeSceneData.sceneTabs || null);

  return {
    sceneId: safeSceneData.sceneId || '',
    title: safeSceneData.title || '',
    background: safeSceneData.background || '',
    items: (safeSceneData.items || []).map(normalizeEntry).filter(Boolean),
    verbs: (safeSceneData.verbs || []).map(normalizeEntry).filter(Boolean),
    prevScene: navigation.prevScene,
    nextScene: navigation.nextScene,
    sceneTabs: navigation.sceneTabs
  };
}

function createScenePage(sceneData) {
  const initialState = buildSceneState(sceneData);

  return {
    data: {
      sceneId: initialState.sceneId,
      title: initialState.title,
      background: initialState.background,
      items: initialState.items,
      verbs: initialState.verbs,
      activeId: '',
      activeType: '',
      activeEntry: null,
      prevScene: initialState.prevScene,
      nextScene: initialState.nextScene,
      sceneTabs: initialState.sceneTabs,
      deviceMode: 'mobile',
      playbackRate: 1.0,
      isLooping: false,
      loading: !initialState.sceneId,
      errorMessage: ''
    },

    initializeScenePage() {
      if (this.scenePageInitialized) {
        return;
      }

      this.scenePageInitialized = true;

      wx.setNavigationBarTitle({
        title: this.data.title || DEFAULT_TITLE
      });

      this.audioContext = wx.createInnerAudioContext();
      this.audioContext.obeyMuteSwitch = false;
      this.audioContext.onError(() => {
        wx.showToast({
          title: '音频播放失败',
          icon: 'none'
        });
      });

      try {
        const savedRate = wx.getStorageSync('preferredPlaybackRate');
        if (savedRate) {
          this.setData({
            playbackRate: parseFloat(savedRate) || 1.0
          });
        }
      } catch (error) {
        console.log('读取播放速度失败', error);
      }
    },

    onLoad() {
      this.initializeScenePage();
    },

    onHide() {
      this.stopAudio();
    },

    onUnload() {
      this.destroyAudio();
    },

    setupScene(nextSceneData) {
      const nextState = buildSceneState(nextSceneData);
      this.setData({
        sceneId: nextState.sceneId,
        title: nextState.title,
        background: nextState.background,
        items: nextState.items,
        verbs: nextState.verbs,
        prevScene: nextState.prevScene,
        nextScene: nextState.nextScene,
        sceneTabs: nextState.sceneTabs,
        activeId: '',
        activeType: '',
        activeEntry: null,
        loading: false,
        errorMessage: ''
      });

      wx.setNavigationBarTitle({
        title: nextState.title || DEFAULT_TITLE
      });
    },

    setLoadError(message) {
      this.setData({
        loading: false,
        errorMessage: message || '场景加载失败'
      });
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

    onRateChange(event) {
      const rate = parseFloat(event.detail.value);
      this.setData({
        playbackRate: rate
      });
      try {
        wx.setStorageSync('preferredPlaybackRate', rate.toString());
      } catch (error) {
        console.log('保存播放速度失败', error);
      }
    },

    onRatePreset(event) {
      const { rate } = event.currentTarget.dataset;
      const rateValue = parseFloat(rate);
      this.setData({
        playbackRate: rateValue
      });
      try {
        wx.setStorageSync('preferredPlaybackRate', rate);
      } catch (error) {
        console.log('保存播放速度失败', error);
      }
      wx.showToast({
        title: rateValue < 1 ? '慢速播放' : '快速播放',
        icon: 'none',
        duration: 800
      });
    },

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

    onOpenCamera() {
      wx.navigateTo({
        url: '/pages/create_scene/index'
      });
    },

    onExportVideo() {
      wx.showModal({
        title: '🎬 导出视频',
        content: '视频导出功能开发中...\n\n将支持：\n• 场景学习记录导出\n• 带配音的视频生成\n• 分享到朋友圈',
        showCancel: false,
        confirmText: '知道了'
      });
    },

    activateEntry(entry, type) {
      this.setData({
        activeId: entry.id,
        activeType: type,
        activeEntry: entry
      });

      this.playAudio(entry);
    },

    navigateToScene(scene) {
      if (!scene || !scene.sceneId || scene.sceneId === this.data.sceneId) {
        return;
      }

      this.stopAudio();
      wx.redirectTo({
        url: scene.route || `/pages/scene_runtime/index?sceneId=${scene.sceneId}`
      });
    },

    playAudio(entry) {
      if (!this.audioContext || !entry.audio) {
        wx.showToast({
          title: '使用在线语音...',
          icon: 'none',
          duration: 1000
        });
        this.simulateTTS(entry);
        return;
      }

      this.audioContext.playbackRate = this.data.playbackRate;
      this.audioContext.stop();
      this.audioContext.src = entry.audio;
      this.audioContext.play();

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

    simulateTTS(entry) {
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
