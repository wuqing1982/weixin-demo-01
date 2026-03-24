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
      sceneTabs
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
        wx.showToast({
          title: '音频不可用',
          icon: 'none'
        });
        return;
      }

      this.audioContext.stop();
      this.audioContext.src = entry.audio;
      this.audioContext.play();
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
