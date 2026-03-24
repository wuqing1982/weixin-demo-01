const sceneData = {
  sceneId: 'cityscape',
  title: '城市景观',
  background: 'https://english.cps.vin/scenes/assets/2026031614361961a1d1.png',
  items: [
    {
      id: 'train',
      word: 'train',
      ipa: '/treɪn/',
      meaning: '火车',
      sentence: 'The train is moving along the tracks.',
      sentenceTranslation: '火车正在轨道上行驶。',
      rect: { l: 57.94, t: 57.60, w: 19.15, h: 17.47 },
      audio: '/assets/audio/cityscape/2026031614361961a1d1_en-US-JennyNeural_US_female_train_the_train_is_moving_along_the.mp3'
    },
    {
      id: 'building',
      word: 'building',
      ipa: '/ˈbɪldɪŋ/',
      meaning: '大楼',
      sentence: 'There are tall buildings in the city.',
      sentenceTranslation: '城市里有高楼大厦。',
      rect: { l: 42.48, t: 14.29, w: 12.01, h: 34.25 },
      audio: '/assets/audio/cityscape/2026031614361961a1d1_en-US-JennyNeural_US_female_building_there_are_tall_buildings_in_the.mp3'
    },
    {
      id: 'car',
      word: 'car',
      ipa: '/kɑːr/',
      meaning: '汽车',
      sentence: 'A car is driving on the road.',
      sentenceTranslation: '一辆车正在马路上行驶。',
      rect: { l: 0.00, t: 91.59, w: 10.25, h: 6.06 },
      audio: '/assets/audio/cityscape/2026031614361961a1d1_en-US-JennyNeural_US_female_car_a_car_is_driving_on_the.mp3'
    },
    {
      id: 'river',
      word: 'river',
      ipa: '/ˈrɪvər/',
      meaning: '河流',
      sentence: 'The river flows through the city.',
      sentenceTranslation: '河流流经这座城市。',
      rect: { l: 0.00, t: 65.86, w: 14.44, h: 5.90 },
      audio: '/assets/audio/cityscape/2026031614361961a1d1_en-US-JennyNeural_US_female_river_the_river_flows_through_the_city.mp3'
    },
    {
      id: 'bridge',
      word: 'bridge',
      ipa: '/brɪdʒ/',
      meaning: '桥',
      sentence: 'There is a bridge over the river.',
      sentenceTranslation: '有一座桥横跨在河上。',
      rect: { l: 16.74, t: 54.30, w: 21.77, h: 6.47 },
      audio: '/assets/audio/cityscape/2026031614361961a1d1_en-US-JennyNeural_US_female_bridge_there_is_a_bridge_over_the.mp3'
    }
  ],
  verbs: [
    {
      id: 'v1',
      word: 'ride',
      ipa: '/raɪd/',
      meaning: '乘坐',
      sentence: 'I like to ride the train.',
      sentenceTranslation: '我喜欢坐火车。',
      audio: '/assets/audio/cityscape/2026031614361961a1d1_en-US-JennyNeural_US_female_v1_i_like_to_ride_the_train.mp3'
    },
    {
      id: 'v2',
      word: 'drive',
      ipa: '/draɪv/',
      meaning: '驾驶',
      sentence: 'My dad drives a car.',
      sentenceTranslation: '我爸爸开车。',
      audio: '/assets/audio/cityscape/2026031614361961a1d1_en-US-JennyNeural_US_female_v2_my_dad_drives_a_car.mp3'
    },
    {
      id: 'v3',
      word: 'cross',
      ipa: '/krɔːs/',
      meaning: '穿过',
      sentence: 'The car crosses the bridge.',
      sentenceTranslation: '汽车穿过桥。',
      audio: '/assets/audio/cityscape/2026031614361961a1d1_en-US-JennyNeural_US_female_v3_the_car_crosses_the_bridge.mp3'
    }
  ]
};

module.exports = sceneData;
