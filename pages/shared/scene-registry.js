const SCENES = [
  {
    sceneId: 'beach_picnic',
    title: '\u6d77\u6ee9\u91ce\u9910',
    route: '/pages/scene/scene'
  },
  {
    sceneId: 'zoo',
    title: '\u52a8\u7269\u56ed',
    route: '/pages/scene_zoo/scene'
  },
  {
    sceneId: 'bedroom',
    title: '\u6e29\u99a8\u5367\u5ba4',
    route: '/pages/scene_bedroom/scene'
  },
  {
    sceneId: 'fruit_bowl',
    title: '\u6c34\u679c\u62fc\u76d8',
    route: '/pages/scene_fruit_bowl/scene'
  },
  {
    sceneId: 'picnic',
    title: '\u91ce\u9910\u65f6\u5149',
    route: '/pages/scene_picnic/scene'
  },
  {
    sceneId: 'breakfast',
    title: '\u8425\u517b\u65e9\u9910',
    route: '/pages/scene_breakfast/scene'
  }
];

function getSceneNeighbors(sceneId) {
  const index = SCENES.findIndex((item) => item.sceneId === sceneId);
  if (index === -1) {
    return {
      prevScene: null,
      nextScene: null,
      sceneTabs: SCENES
    };
  }

  return {
    prevScene: SCENES[index - 1] || null,
    nextScene: SCENES[index + 1] || null,
    sceneTabs: SCENES
  };
}

module.exports = {
  SCENES,
  getSceneNeighbors
};
