const sceneData = require('./scene-data');

Page({
  data: {
    title: sceneData.title,
    background: sceneData.background,
    items: sceneData.items,
    activeId: '',
    activeItem: null
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

  onUnload() {
    this.destroyAudio();
  },

  onHide() {
    this.stopAudio();
  },

  onTapHotspot(event) {
    const { id } = event.currentTarget.dataset;
    const item = this.data.items.find((entry) => entry.id === id);

    if (!item) {
      return;
    }

    this.setData({
      activeId: item.id,
      activeItem: item
    });

    this.playAudio(item);
  },

  onCloseOverlay() {
    this.stopAudio();
    this.setData({
      activeId: '',
      activeItem: null
    });
  },

  playAudio(item) {
    if (!this.audioContext || !item.audio) {
      wx.showToast({
        title: '音频不可用',
        icon: 'none'
      });
      return;
    }

    this.audioContext.stop();
    this.audioContext.src = item.audio;
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
});
