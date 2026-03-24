const sceneData = {
  sceneId: 'zoo',
  title: '动物园',
  background: '/assets/images/zoo.png',
  items: [
    {
      id: 'panda_1',
      word: 'panda',
      ipa: '/ˈpeɪndə/',
      meaning: '大熊猫',
      sentence: 'The panda is sitting on the swing.',
      sentenceTranslation: '熊猫正坐在秋千上。',
      rect: { l: 60, t: 50, w: 20, h: 20 },
      audio: '/assets/audio/zoo/zoo_en-US-JennyNeural_US_female_panda_1_the_panda_is_sitting_on_the.mp3'
    },
    {
      id: 'panda_2',
      word: 'swing',
      ipa: '/swɪŋ/',
      meaning: '秋千',
      sentence: 'The panda is playing on the swing.',
      sentenceTranslation: '熊猫正在玩秋千。',
      rect: { l: 40, t: 70, w: 30, h: 30 },
      audio: '/assets/audio/zoo/zoo_en-US-JennyNeural_US_female_panda_2_the_panda_is_playing_on_the.mp3'
    },
    {
      id: 'building',
      word: 'building',
      ipa: '/ˈbɪldɪŋ/',
      meaning: '建筑',
      sentence: 'The building is behind the pandas.',
      sentenceTranslation: '建筑在熊猫后面。',
      rect: { l: 10, t: 10, w: 40, h: 40 },
      audio: '/assets/audio/zoo/zoo_en-US-JennyNeural_US_female_building_the_building_is_behind_the_pandas.mp3'
    },
    {
      id: 'grass',
      word: 'grass',
      ipa: '/grɑːs/',
      meaning: '草地',
      sentence: 'The grass is green and lush.',
      sentenceTranslation: '草很绿很茂盛。',
      rect: { l: 10, t: 50, w: 30, h: 30 },
      audio: '/assets/audio/zoo/zoo_en-US-JennyNeural_US_female_grass_the_grass_is_green_and_lush.mp3'
    },
    {
      id: 'tire',
      word: 'tire',
      ipa: '/taɪr/',
      meaning: '轮胎',
      sentence: 'There are two tires on the ground.',
      sentenceTranslation: '地上有两个轮胎。',
      rect: { l: 80, t: 90, w: 10, h: 10 },
      audio: '/assets/audio/zoo/zoo_en-US-JennyNeural_US_female_tire_there_are_two_tires_on_the.mp3'
    }
  ],
  verbs: [
    {
      id: 'play',
      word: 'play',
      ipa: '/pleɪ/',
      meaning: '玩耍',
      sentence: 'The panda plays on the swing.',
      sentenceTranslation: '熊猫在秋千上玩耍。',
      audio: '/assets/audio/zoo/zoo_en-US-JennyNeural_US_female_play_the_panda_plays_on_the_swing.mp3'
    },
    {
      id: 'sit',
      word: 'sit',
      ipa: '/sɪt/',
      meaning: '坐下',
      sentence: 'The panda sits on the swing.',
      sentenceTranslation: '熊猫坐在秋千上。',
      audio: '/assets/audio/zoo/zoo_en-US-JennyNeural_US_female_sit_the_panda_sits_on_the_swing.mp3'
    },
    {
      id: 'eat',
      word: 'eat',
      ipa: '/iːt/',
      meaning: '吃',
      sentence: 'The panda eats bamboo while sitting on the swing.',
      sentenceTranslation: '熊猫坐在秋千上吃竹子。',
      audio: '/assets/audio/zoo/zoo_en-US-JennyNeural_US_female_eat_the_panda_eats_bamboo_while_sitting.mp3'
    }
  ]
};

module.exports = sceneData;
