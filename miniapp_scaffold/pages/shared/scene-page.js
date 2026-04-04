const { getSceneNeighbors } = require('./scene-registry');

const SWIPE_DISTANCE = 70;
const SWIPE_VERTICAL_TOLERANCE = 80;

function normalizeEntry(entry) {
  if (!entry) {
    return null;
  }

  return Object.assign({}, entry, {
    sentenceTranslation: entry.sentenceTranslation || entry.sentence_translation || ''
  });
}

function findEntryById(entries, id) {
  return (entries || []).find((entry) => entry.id === id) || null;
}

function createScenePage() {
  return {
    data: {
      sceneId: '',
      title: '',
      background: '',
      items: [],
      verbs: [],
      activeId: '',
      activeType: '',
      activeEntry: null,
      prevScene: null,
      nextScene: null,
      sceneTabs: [],
      deviceMode: 'mobile',
      playbackRate: 1,
      isLooping: false,
      loading: true,
      errorMessage: ''
    },

    setupScene(sceneData) {
      const { prevScene, nextScene, sceneTabs } = getSceneNeighbors(sceneData.sceneId);
      this.setData({
        sceneId: sceneData.sceneId,
        title: sceneData.title,
        background: sceneData.background,
        items: (sceneData.items || []).map(normalizeEntry),
        verbs: (sceneData.verbs || []).map(normalizeEntry),
        prevScene,
        nextScene,
        sceneTabs,
        loading: false,
        errorMessage: '',
        activeId: '',
        activeType: '',
        activeEntry: null
      });
      wx.setNavigationBarTitle({
        title: sceneData.title || '英语场景'
      });
    },

    onTouchStart(event) {
      const touch = event.changedTouches && event.changedTouches[0];
      if (!touch) {
        return;
      }
      this.touchStartPoint = { x: touch.pageX, y: touch.pageY };
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
      if (item) {
        this.activateEntry(item, 'item');
      }
    },

    onTapVerb(event) {
      const { id } = event.currentTarget.dataset;
      const verb = findEntryById(this.data.verbs, id);
      if (verb) {
        this.activateEntry(verb, 'verb');
      }
    },

    onCloseOverlay() {
      this.stopAudio();
      this.setData({
        activeId: '',
        activeType: '',
        activeEntry: null
      });
    },

    onSwitchDevice(event) {
      this.setData({
        deviceMode: event.currentTarget.dataset.mode
      });
    },

    onRateChange(event) {
      const rate = parseFloat(event.detail.value);
      this.setData({ playbackRate: rate });
      wx.setStorageSync('preferredPlaybackRate', String(rate));
    },

    onRatePreset(event) {
      const rate = parseFloat(event.currentTarget.dataset.rate);
      this.setData({ playbackRate: rate });
      wx.setStorageSync('preferredPlaybackRate', String(rate));
    },

    onToggleLoop() {
      this.setData({ isLooping: !this.data.isLooping });
    },

    onTapScenePill(event) {
      const target = this.data.sceneTabs.find((item) => item.sceneId === event.currentTarget.dataset.sceneId);
      this.navigateToScene(target);
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

      wx.redirectTo({
        url: `/pages/scene_runtime/index?sceneId=${scene.sceneId}`
      });
    },

    playAudio(entry) {
      if (!entry || !entry.audio) {
        return;
      }

      if (!this.audioContext) {
        this.audioContext = wx.createInnerAudioContext();
        this.audioContext.obeyMuteSwitch = false;
      }

      this.audioContext.stop();
      this.audioContext.playbackRate = this.data.playbackRate || 1;
      this.audioContext.src = entry.audio;
      this.audioContext.play();
    },

    stopAudio() {
      if (this.audioContext) {
        this.audioContext.stop();
      }
    },

    onUnload() {
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
