const { getMyVideoExports } = require('../../services/scene');
const { getConfig } = require('../../services/config');

Page({
  data: {
    loading: true,
    videos: [],
    errorMessage: ''
  },

  onShow() {
    this.loadVideos();
  },

  onPullDownRefresh() {
    this.loadVideos().finally(() => {
      wx.stopPullDownRefresh();
    });
  },

  async loadVideos() {
    this.setData({ loading: true, errorMessage: '' });
    try {
      const data = await getMyVideoExports();
      const list = (data.list || []).map(item => {
        if (item.videoUrl && !item.videoUrl.startsWith('http')) {
          const { apiBaseUrl } = getConfig();
          item.videoUrl = apiBaseUrl + item.videoUrl;
        }
        if (item.coverUrl && !item.coverUrl.startsWith('http')) {
          const { apiBaseUrl } = getConfig();
          item.coverUrl = apiBaseUrl + item.coverUrl;
        }
        return item;
      });
      this.setData({ loading: false, videos: list });
    } catch (error) {
      this.setData({
        loading: false,
        errorMessage: error.message || '视频列表加载失败'
      });
    }
  },

  onPlayVideo(event) {
    const { index } = event.currentTarget.dataset;
    const video = this.data.videos[index];
    if (!video || !video.videoUrl) {
      wx.showToast({ title: '视频地址无效', icon: 'none' });
      return;
    }
    wx.previewMedia({
      sources: [{ url: video.videoUrl, type: 'video' }],
      current: 0
    });
  }
});
