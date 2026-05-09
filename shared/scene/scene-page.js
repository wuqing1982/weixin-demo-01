const { saveSceneHotspots, startVideoExport, getVideoExportStatus } = require('../../services/scene');
const {
  normalizeEditorRect,
  applyMoveDelta,
  applyResizeDelta,
  normalizeFloatingButtonPosition,
  applyFloatingButtonDelta
} = require('./hotspot-editor');
const { getSceneNeighbors } = require('./scene-registry');

const SWIPE_DISTANCE = 70;
const SWIPE_VERTICAL_TOLERANCE = 80;
const DEFAULT_TITLE = '英语场景';
const DEFAULT_SAVE_BUTTON_POSITION = {
  left: 10,
  top: 80
};

function findEntryById(entries, id) {
  return (entries || []).find((entry) => entry.id === id) || null;
}

function cloneEntries(entries) {
  return JSON.parse(JSON.stringify(entries || []));
}

function normalizeEntry(entry) {
  if (!entry) {
    return null;
  }

  return Object.assign({}, entry, {
    sentenceTranslation: entry.sentenceTranslation || entry.sentence_translation || '',
    rect: entry.rect ? normalizeEditorRect(entry.rect) : null
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
    cover: safeSceneData.cover || '',
    items: (safeSceneData.items || []).map(normalizeEntry).filter(Boolean),
    verbs: (safeSceneData.verbs || []).map(normalizeEntry).filter(Boolean),
    prevScene: navigation.prevScene,
    nextScene: navigation.nextScene,
    sceneTabs: navigation.sceneTabs,
    capabilities: safeSceneData.capabilities || {},
    canEditHotspots: !!(safeSceneData.capabilities && safeSceneData.capabilities.canEditHotspots)
  };
}

function createScenePage(sceneData) {
  const initialState = buildSceneState(sceneData);

  return {
    data: {
      sceneId: initialState.sceneId,
      title: initialState.title,
      background: initialState.background,
      cover: initialState.cover,
      items: initialState.items,
      hotspotItems: initialState.items,
      draftItems: [],
      verbs: initialState.verbs,
      activeId: '',
      activeType: '',
      activeEntry: null,
      prevScene: initialState.prevScene,
      nextScene: initialState.nextScene,
      sceneTabs: initialState.sceneTabs,
      capabilities: initialState.capabilities,
      canEditHotspots: initialState.canEditHotspots,
      editorMode: false,
      editingItemId: '',
      editingEntry: null,
      isDirty: false,
      isSaving: false,
      isDraggingSaveHandle: false,
      saveButtonPosition: normalizeFloatingButtonPosition(DEFAULT_SAVE_BUTTON_POSITION),
      deviceMode: 'mobile',
      playbackRate: 1.0,
      playbackRateLabel: '1.0',
      isLooping: false,
      loading: !initialState.sceneId,
      errorMessage: '',
      showPhoneBindModal: false
    },

    initializeScenePage() {
      if (this.scenePageInitialized) {
        return;
      }

      this.scenePageInitialized = true;
      this.stageMetrics = null;
      this.dragState = null;
      this.saveButtonDragState = null;
      this.viewportRect = this.getViewportRect();

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
            playbackRate: parseFloat(savedRate) || 1.0,
            playbackRateLabel: (parseFloat(savedRate) || 1.0).toFixed(1),
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
      this.dragState = null;
      this.saveButtonDragState = null;
      this.destroyAudio();
    },

    setupScene(nextSceneData) {
      const nextState = buildSceneState(nextSceneData);
      this.setData({
        sceneId: nextState.sceneId,
        title: nextState.title,
        background: nextState.background,
        items: nextState.items,
        hotspotItems: nextState.items,
        draftItems: [],
        verbs: nextState.verbs,
        prevScene: nextState.prevScene,
        nextScene: nextState.nextScene,
        sceneTabs: nextState.sceneTabs,
        capabilities: nextState.capabilities,
        canEditHotspots: nextState.canEditHotspots,
        editorMode: false,
        editingItemId: '',
        editingEntry: null,
        isDirty: false,
        isSaving: false,
        isDraggingSaveHandle: false,
        saveButtonPosition: normalizeFloatingButtonPosition(DEFAULT_SAVE_BUTTON_POSITION, this.viewportRect),
        activeId: '',
        activeType: '',
        activeEntry: null,
        loading: false,
        errorMessage: ''
      });
      this.stageMetrics = null;
      this.dragState = null;
      this.saveButtonDragState = null;

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
      if (this.data.editorMode) {
        return;
      }

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
      if (this.data.editorMode) {
        return;
      }

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
      const item = findEntryById(this.data.editorMode ? this.data.draftItems : this.data.items, id);

      if (!item) {
        return;
      }

      if (this.data.editorMode) {
        this.selectEditingItem(item.id);
        return;
      }

      this.activateEntry(item, 'item');
    },

    onTapVerb(event) {
      if (this.data.editorMode) {
        return;
      }

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
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }
      this.navigateToScene(this.data.prevScene);
    },

    onTapNextScene() {
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }
      this.navigateToScene(this.data.nextScene);
    },

    onTapScenePill(event) {
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }

      const { sceneId } = event.currentTarget.dataset;
      const targetScene = this.data.sceneTabs.find((item) => item.sceneId === sceneId);
      this.navigateToScene(targetScene);
    },

    _applyPlaybackRate(ctx, rate) {
      if (!ctx) return;
      ctx.playbackRate = rate;
    },

    onRateChange(event) {
      const rate = parseFloat(event.detail.value);
      this.setData({ playbackRate: rate, playbackRateLabel: rate.toFixed(1) });
      try {
        wx.setStorageSync('preferredPlaybackRate', rate.toString());
      } catch (e) { /* ignore */ }
      this._applyPlaybackRate(this.audioContext, rate);
      this._applyPlaybackRate(this.ttsAudioContext, rate);
    },

    onRatePreset(event) {
      const { rate } = event.currentTarget.dataset;
      const rateValue = parseFloat(rate);
      this.setData({ playbackRate: rateValue, playbackRateLabel: rateValue.toFixed(1) });
      try {
        wx.setStorageSync('preferredPlaybackRate', rate);
      } catch (e) { /* ignore */ }
      this._applyPlaybackRate(this.audioContext, rateValue);
      this._applyPlaybackRate(this.ttsAudioContext, rateValue);
      wx.showToast({
        title: rateValue < 1 ? '慢速播放' : '快速播放',
        icon: 'none',
        duration: 800
      });
    },

    onToggleLoop() {
      const newLoopState = !this.data.isLooping;
      this.setData({ isLooping: newLoopState });
      if (this.audioContext) {
        this.audioContext.loop = newLoopState;
      }
      if (this.ttsAudioContext) {
        this.ttsAudioContext.loop = newLoopState;
      }
      wx.showToast({
        title: newLoopState ? '循环播放已开启' : '循环播放已关闭',
        icon: 'none',
        duration: 1200
      });
    },

    onOpenCamera() {
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }

      wx.navigateTo({
        url: '/pages/create_scene/index'
      });
    },

    async onExportVideo() {
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }

      let currentUser = getApp().globalData.currentUser;
      if (!currentUser) {
        try {
          const { getMe } = require('../../services/user');
          currentUser = await getMe();
          getApp().globalData.currentUser = currentUser;
        } catch (_) {
          currentUser = null;
        }
      }
      if (currentUser && !currentUser.mobileVerified) {
        this.setData({ showPhoneBindModal: true });
        return;
      }

      const sceneId = this.data.sceneId;
      if (!sceneId) {
        wx.showToast({ title: '场景信息缺失', icon: 'none' });
        return;
      }

      if (this._exporting) {
        wx.showToast({ title: '正在导出中...', icon: 'none' });
        return;
      }

      wx.showModal({
        title: '导出学习视频',
        content: '将为此场景生成带热点标注和配音的学习视频，确定导出吗？',
        success: (res) => {
          if (!res.confirm) return;
          this._doExportVideo(sceneId);
        }
      });
    },

    async _doExportVideo(sceneId) {
      this._exporting = true;
      wx.showLoading({ title: '提交导出任务...', mask: true });

      try {
        const data = await startVideoExport(sceneId);
        const jobId = data.jobId;
        wx.hideLoading();

        if (!jobId) {
          this._exporting = false;
          wx.showToast({ title: '导出任务创建失败', icon: 'none' });
          return;
        }

        // Show progress dialog
        this._exportJobId = jobId;
        this.setData({
          exportProgress: 0,
          exportMessage: '准备中...',
          exportJobId: jobId
        });

        this._showExportProgressDialog();

        // Poll for status (don't clear _exporting here - poll handles it)
        this._pollExportStatus(jobId);
      } catch (err) {
        wx.hideLoading();
        this._exporting = false;
        const msg = (err && (err.message || err.errMsg)) || '导出失败';
        wx.showModal({
          title: '导出失败',
          content: String(msg),
          showCancel: false
        });
      }
    },

    _showExportProgressDialog() {
      wx.showLoading({
        title: '导出中 0%',
        mask: true
      });
    },

    async _pollExportStatus(jobId) {
      let retries = 0;
      const maxRetries = 120; // 2 minutes max at 1s interval

      const poll = async () => {
        try {
          const data = await getVideoExportStatus(jobId);
          const progress = data.progress || 0;
          const message = data.message || '';
          const status = data.status || '';

          console.log('[video-export] poll:', JSON.stringify({ status, progress, videoUrl: data.videoUrl ? 'has-url' : 'empty' }));

          if (status === 'completed') {
            wx.hideLoading();
            this._exporting = false;
            wx.showToast({ title: '导出完成', icon: 'success' });
            setTimeout(() => {
              wx.navigateTo({ url: '/pages/my_videos/index' });
            }, 1500);
            return;
          }

          if (status === 'failed') {
            wx.hideLoading();
            this._exporting = false;
            wx.showModal({
              title: '导出失败',
              content: message || '视频生成过程中出错',
              showCancel: false
            });
            return;
          }

          // Still processing - update loading title
          wx.hideLoading();
          wx.showLoading({
            title: `导出中 ${progress}%`,
            mask: true
          });

          retries++;
          if (retries < maxRetries) {
            setTimeout(poll, 1000);
          } else {
            wx.hideLoading();
            this._exporting = false;
            wx.showToast({ title: '导出超时，请稍后重试', icon: 'none', duration: 3000 });
          }
        } catch (err) {
          retries++;
          if (retries < maxRetries) {
            setTimeout(poll, 2000);
          } else {
            wx.hideLoading();
            this._exporting = false;
            wx.showToast({ title: '查询状态失败', icon: 'none' });
          }
        }
      };

      // Start polling after 1 second
      setTimeout(poll, 1000);
    },

    onPhoneBindSuccess() {
      const sceneId = this.data.sceneId;
      this.setData({ showPhoneBindModal: false });
      if (sceneId && !this._exporting) {
        this._doExportVideo(sceneId);
      }
    },

    onPhoneBindClose() {
      this.setData({ showPhoneBindModal: false });
    },

    _resolveFullUrl(videoUrl) {
      const { staticBaseUrl } = require('../../services/config').getConfig();
      return videoUrl.startsWith('http')
        ? videoUrl
        : `${staticBaseUrl}${videoUrl.startsWith('/') ? '' : '/'}${videoUrl}`;
    },

    _downloadAndSaveVideo(videoUrl) {
      const fullUrl = this._resolveFullUrl(videoUrl);
      wx.showLoading({ title: '下载视频中...', mask: true });

      const downloadTask = wx.downloadFile({
        url: fullUrl,
        success: (res) => {
          if (res.statusCode === 200) {
            wx.saveVideoToPhotosAlbum({
              filePath: res.tempFilePath,
              success: () => {
                wx.hideLoading();
                wx.showToast({ title: '已保存到相册', icon: 'success' });
              },
              fail: (err) => {
                wx.hideLoading();
                const errMsg = (err && err.errMsg) || '';
                if (errMsg.indexOf('auth deny') !== -1 || errMsg.indexOf('authorize') !== -1) {
                  wx.showModal({
                    title: '需要授权',
                    content: '请在设置中允许访问相册，然后重试。',
                    confirmText: '去设置',
                    success: (modalRes) => {
                      if (modalRes.confirm) {
                        wx.openSetting();
                      }
                    }
                  });
                } else {
                  wx.showModal({
                    title: '保存失败',
                    content: errMsg || '保存到相册失败，请重试。',
                    showCancel: false
                  });
                }
              }
            });
          } else {
            wx.hideLoading();
            wx.showToast({ title: '下载失败', icon: 'none' });
          }
        },
        fail: () => {
          wx.hideLoading();
          wx.showToast({ title: '下载失败，请检查网络', icon: 'none' });
        }
      });

      downloadTask.onProgressUpdate((res) => {
        wx.showLoading({ title: `下载 ${res.progress}%`, mask: true });
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
      if (this.data.editorMode) {
        this.showEditorToast();
        return;
      }

      if (!scene || !scene.sceneId || scene.sceneId === this.data.sceneId) {
        return;
      }

      this.stopAudio();
      wx.redirectTo({
        url: scene.route || `/pages/scene_runtime/index?sceneId=${scene.sceneId}`
      });
    },

    playAudio(entry) {
      let audioSrc = entry.audio || entry.audioPath || '';
      if (audioSrc && !audioSrc.startsWith('http')) {
        const { staticBaseUrl } = require('../../services/config').getConfig();
        audioSrc = `${staticBaseUrl}${audioSrc.startsWith('/') ? '' : '/'}${audioSrc}`;
      }
      if (!this.audioContext || !audioSrc) {
        this.simulateTTS(entry);
        return;
      }

      const rate = this.data.playbackRate;
      this.audioContext.stop();
      this.audioContext.offPlay();
      this.audioContext.loop = this.data.isLooping;

      // playbackRate must be set inside onPlay — direct/timeout/canplay setting
      // has no effect on real devices (WeChat known issue)
      this.audioContext.onPlay(() => {
        if (this.audioContext) {
          this.audioContext.playbackRate = rate;
        }
      });

      this.audioContext.src = audioSrc;
      this.audioContext.play();
    },

    simulateTTS(entry) {
      const { getTtsUrl } = require('../../services/scene');
      // Live TTS: only reads sentence (to distinguish from pre-generated MP3)
      const text = entry.sentence || entry.word || '';
      if (!text) {
        return;
      }
      const ttsUrl = getTtsUrl(text);
      const rate = this.data.playbackRate;
      if (this.ttsAudioContext) {
        this.ttsAudioContext.stop();
        this.ttsAudioContext.destroy();
      }
      this.ttsAudioContext = wx.createInnerAudioContext();
      this.ttsAudioContext.obeyMuteSwitch = false;
      this.ttsAudioContext.loop = this.data.isLooping;
      this.ttsAudioContext.onError((err) => {
        console.log('TTS audio error', err);
      });

      this.ttsAudioContext.onPlay(() => {
        if (this.ttsAudioContext) {
          this.ttsAudioContext.playbackRate = rate;
        }
      });

      this.ttsAudioContext.src = ttsUrl;
      this.ttsAudioContext.play();
    },

    showEditorToast(message) {
      wx.showToast({
        title: message || '请先保存或退出编辑',
        icon: 'none',
        duration: 1200
      });
    },

    measureStageRect() {
      return new Promise((resolve) => {
        wx.nextTick(() => {
          this.createSelectorQuery()
            .select('#sceneContent')
            .boundingClientRect((rect) => {
              this.stageMetrics = rect || null;
              resolve(rect || null);
            })
            .exec();
        });
      });
    },

    selectEditingItem(itemId) {
      const entry = findEntryById(this.data.draftItems, itemId);
      if (!entry) {
        return;
      }

      this.setData({
        editingItemId: entry.id,
        editingEntry: entry,
        activeId: '',
        activeType: '',
        activeEntry: null
      });
    },

    getViewportRect() {
      try {
        if (typeof wx.getWindowInfo === 'function') {
          const info = wx.getWindowInfo();
          return {
            width: info.windowWidth || 375,
            height: info.windowHeight || 667
          };
        }
        const info = wx.getSystemInfoSync();
        return {
          width: info.windowWidth || 375,
          height: info.windowHeight || 667
        };
      } catch (error) {
        return {
          width: 375,
          height: 667
        };
      }
    },

    async enterEditorMode() {
      if (this.data.loading || this.data.isSaving) {
        return;
      }

      if (!this.data.canEditHotspots) {
        wx.showToast({ title: '无权限编辑此场景热点', icon: 'none', duration: 2000 });
        return;
      }

      if (this.data.editorMode) {
        return;
      }

      const draftItems = cloneEntries(this.data.items);
      const firstItem = draftItems[0] || null;
      this.stopAudio();
      this.setData({
        editorMode: true,
        draftItems,
        hotspotItems: draftItems,
        editingItemId: firstItem ? firstItem.id : '',
        editingEntry: firstItem,
        isDirty: false,
        activeId: '',
        activeType: '',
        activeEntry: null
      });
      this.viewportRect = this.getViewportRect();
      this.setData({
        saveButtonPosition: normalizeFloatingButtonPosition(
          this.data.saveButtonPosition || DEFAULT_SAVE_BUTTON_POSITION,
          this.viewportRect
        )
      });
      await this.measureStageRect();
    },

    exitEditorMode() {
      if (!this.data.editorMode) {
        return;
      }

      if (!this.data.isDirty) {
        this.setData({
          editorMode: false,
          draftItems: [],
          hotspotItems: this.data.items,
          editingItemId: '',
          editingEntry: null
        });
        this.dragState = null;
        this.saveButtonDragState = null;
        return;
      }

      wx.showModal({
        title: '放弃未保存改动？',
        content: '当前热点位置还没有保存，退出后会丢失这些修改。',
        success: (result) => {
          if (!result.confirm) {
            return;
          }

          this.setData({
            editorMode: false,
            draftItems: [],
            hotspotItems: this.data.items,
            editingItemId: '',
            editingEntry: null,
            isDirty: false
          });
          this.dragState = null;
          this.saveButtonDragState = null;
        }
      });
    },

    async onEnterEditorMode() {
      await this.enterEditorMode();
    },

    onExitEditorMode() {
      this.exitEditorMode();
    },

    updateDraftRect(itemId, rect, options = {}) {
      const nextDraftItems = cloneEntries(this.data.draftItems);
      const index = nextDraftItems.findIndex((item) => item.id === itemId);

      if (index < 0) {
        return;
      }

      nextDraftItems[index].rect = normalizeEditorRect(rect);
      const editingEntry = nextDraftItems[index];
      this.setData({
        draftItems: nextDraftItems,
        hotspotItems: nextDraftItems,
        editingItemId: itemId,
        editingEntry,
        isDirty: options.markDirty === false ? this.data.isDirty : true
      });
    },

    onEditorZoneTouchStart(event) {
      if (!this.data.editorMode || this.data.isSaving) {
        return;
      }

      const touch = event.touches && event.touches[0];
      const { id } = event.currentTarget.dataset;
      const item = findEntryById(this.data.draftItems, id);

      if (!touch || !item || !item.rect) {
        return;
      }

      this.selectEditingItem(id);
      this.dragState = {
        itemId: id,
        mode: 'move',
        startX: touch.pageX,
        startY: touch.pageY,
        startRect: Object.assign({}, item.rect)
      };
    },

    onEditorHandleTouchStart(event) {
      if (!this.data.editorMode || this.data.isSaving) {
        return;
      }

      const touch = event.touches && event.touches[0];
      const { id, handle } = event.currentTarget.dataset;
      const item = findEntryById(this.data.draftItems, id);

      if (!touch || !item || !item.rect || !handle) {
        return;
      }

      this.selectEditingItem(id);
      this.dragState = {
        itemId: id,
        mode: 'resize',
        handle,
        startX: touch.pageX,
        startY: touch.pageY,
        startRect: Object.assign({}, item.rect)
      };
    },

    onEditorZoneTouchMove(event) {
      if (!this.data.editorMode || !this.dragState || this.data.isSaving) {
        return;
      }

      const touch = event.touches && event.touches[0];
      const metrics = this.stageMetrics;

      if (!touch || !metrics || !metrics.width || !metrics.height) {
        return;
      }

      const deltaX = ((touch.pageX - this.dragState.startX) / metrics.width) * 100;
      const deltaY = ((touch.pageY - this.dragState.startY) / metrics.height) * 100;
      const nextRect = this.dragState.mode === 'resize'
        ? applyResizeDelta(this.dragState.startRect, this.dragState.handle, deltaX, deltaY)
        : applyMoveDelta(this.dragState.startRect, deltaX, deltaY);
      this.updateDraftRect(this.dragState.itemId, nextRect);
    },

    onEditorZoneTouchEnd() {
      this.dragState = null;
    },

    onSaveButtonTouchStart(event) {
      if (!this.data.editorMode || this.data.isSaving) {
        return;
      }

      const touch = event.touches && event.touches[0];
      if (!touch) {
        return;
      }

      this.saveButtonDragState = {
        startX: touch.pageX,
        startY: touch.pageY,
        startPosition: Object.assign({}, this.data.saveButtonPosition)
      };
      this.setData({
        isDraggingSaveHandle: true
      });
    },

    onSaveButtonTouchMove(event) {
      if (!this.data.editorMode || !this.saveButtonDragState || this.data.isSaving) {
        return;
      }

      const touch = event.touches && event.touches[0];
      if (!touch) {
        return;
      }

      const deltaX = touch.pageX - this.saveButtonDragState.startX;
      const deltaY = touch.pageY - this.saveButtonDragState.startY;
      this.viewportRect = this.viewportRect || this.getViewportRect();
      const nextPosition = applyFloatingButtonDelta(
        this.saveButtonDragState.startPosition,
        deltaX,
        deltaY,
        this.viewportRect
      );

      this.setData({
        saveButtonPosition: nextPosition
      });
    },

    onSaveButtonTouchEnd() {
      this.saveButtonDragState = null;
      if (this.data.isDraggingSaveHandle) {
        this.setData({
          isDraggingSaveHandle: false
        });
      }
    },

    onSaveButtonTouchCancel() {
      this.onSaveButtonTouchEnd();
    },

    onTapFloatingSave() {
      this.onSaveHotspots();
    },

    onEditorNudge(event) {
      if (!this.data.editorMode || !this.data.editingItemId || this.data.isSaving) {
        return;
      }

      const item = findEntryById(this.data.draftItems, this.data.editingItemId);
      if (!item || !item.rect) {
        return;
      }

      const { dl, dt, dw, dh } = event.currentTarget.dataset;
      this.updateDraftRect(item.id, {
        l: item.rect.l + (parseFloat(dl) || 0),
        t: item.rect.t + (parseFloat(dt) || 0),
        w: item.rect.w + (parseFloat(dw) || 0),
        h: item.rect.h + (parseFloat(dh) || 0)
      });
    },

    onEditorResetCurrent() {
      if (!this.data.editorMode || !this.data.editingItemId || this.data.isSaving) {
        return;
      }

      const sourceItem = findEntryById(this.data.items, this.data.editingItemId);
      if (!sourceItem || !sourceItem.rect) {
        return;
      }

      this.updateDraftRect(sourceItem.id, sourceItem.rect);
    },

    async onSaveHotspots() {
      if (!this.data.editorMode || !this.data.isDirty || this.data.isSaving) {
        return;
      }

      this.setData({
        isSaving: true
      });

      try {
        const detail = await saveSceneHotspots(
          this.data.sceneId,
          (this.data.draftItems || []).map((item) => ({
            id: item.id,
            rect: item.rect
          }))
        );

        this.setupScene(Object.assign({}, detail, {
          sceneTabs: this.data.sceneTabs
        }));

        wx.showToast({
          title: '热点已保存',
          icon: 'success',
          duration: 1200
        });
      } catch (error) {
        this.setData({
          isSaving: false
        });
        wx.showToast({
          title: error.message || '热点保存失败',
          icon: 'none',
          duration: 1500
        });
      }
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
      if (this.ttsAudioContext) {
        this.ttsAudioContext.stop();
        this.ttsAudioContext.destroy();
        this.ttsAudioContext = null;
      }
    }
  };
}

module.exports = {
  createScenePage
};
