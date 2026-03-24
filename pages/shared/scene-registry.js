const SCENES = [
  {
    sceneId: 'cityscape',
    title: '城市景观',
    route: '/pages/scene_city/scene'
  },
  {
    sceneId: 'beach_picnic',
    title: '海滩野餐',
    route: '/pages/scene/scene'
  },
  {
    sceneId: 'zoo',
    title: '动物园',
    route: '/pages/scene_zoo/scene'
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
