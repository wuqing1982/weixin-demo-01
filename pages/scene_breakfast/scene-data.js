const sceneData = {
  sceneId: 'breakfast',
  title: '\u8425\u517b\u65e9\u9910',
  background: '/assets/images/breakfast.jpg',
  items: [
    {
      id: 'porridge',
      word: 'porridge',
      ipa: '/porridʒ/',
      meaning: '\u7ca5',
      sentence: 'I eat porridge for breakfast.',
      sentenceTranslation: '\u6211\u65e9\u9910\u5403\u7ca5\u3002',
      rect: { l: 13.5, t: 24.5, w: 50.2, h: 15.0 },
      audio: '/assets/audio/breakfast/breakfast_en-US-JennyNeural_US_female_porridge_i_eat_porridge_for_breakfast.mp3'
    },
    {
      id: 'corn',
      word: 'corn',
      ipa: '/kɔːrn/',
      meaning: '\u7389\u7c73',
      sentence: 'There is a corn on the plate.',
      sentenceTranslation: '\u76d8\u5b50\u91cc\u6709\u4e00\u6839\u7389\u7c73\u3002',
      rect: { l: 70.8, t: 45.8, w: 30.2, h: 25.0 },
      audio: '/assets/audio/breakfast/breakfast_en-US-JennyNeural_US_female_corn_there_is_a_corn_on_the.mp3'
    },
    {
      id: 'sweet_potato',
      word: 'sweet potato',
      ipa: '/swiːt pəteɪtoʊ/',
      meaning: '\u7ea2\u85af',
      sentence: 'The sweet potato is brown and orange.',
      sentenceTranslation: '\u7ea2\u85af\u662f\u68d5\u8272\u548c\u6a59\u8272\u7684\u3002',
      rect: { l: 48.2, t: 47.2, w: 25.0, h: 20.0 },
      audio: '/assets/audio/breakfast/breakfast_en-US-JennyNeural_US_female_sweet_potato_the_sweet_potato_is_brown_and.mp3'
    },
    {
      id: 'boiled_egg',
      word: 'boiled egg',
      ipa: '/bɔɪld eɡ/',
      meaning: '\u716e\u9e21\u86cb',
      sentence: 'I have two boiled eggs.',
      sentenceTranslation: '\u6211\u6709\u4e24\u4e2a\u716e\u9e21\u86cb\u3002',
      rect: { l: 49.6, t: 62.0, w: 22.0, h: 15.0 },
      audio: '/assets/audio/breakfast/breakfast_en-US-JennyNeural_US_female_boiled_egg_i_have_two_boiled_eggs.mp3'
    },
    {
      id: 'dumpling',
      word: 'dumpling',
      ipa: '/dʌmplɪŋ/',
      meaning: '\u997a\u5b50',
      sentence: 'There are two dumplings on the plate.',
      sentenceTranslation: '\u76d8\u5b50\u91cc\u6709\u4e24\u4e2a\u997a\u5b50\u3002',
      rect: { l: 56.0, t: 71.2, w: 25.0, h: 15.0 },
      audio: '/assets/audio/breakfast/breakfast_en-US-JennyNeural_US_female_dumpling_there_are_two_dumplings_on_the.mp3'
    }
  ],
  verbs: [
    {
      id: 'v1',
      word: 'eat',
      ipa: '/iːt/',
      meaning: '\u5403',
      sentence: 'I eat boiled eggs.',
      sentenceTranslation: '\u6211\u5403\u716e\u9e21\u86cb\u3002',
      audio: '/assets/audio/breakfast/breakfast_en-US-JennyNeural_US_female_v1_i_eat_boiled_eggs.mp3'
    },
    {
      id: 'v2',
      word: 'cook',
      ipa: '/kʊk/',
      meaning: '\u716e',
      sentence: 'We cook porridge for breakfast.',
      sentenceTranslation: '\u6211\u4eec\u716e\u7ca5\u5f53\u65e9\u9910\u3002',
      audio: '/assets/audio/breakfast/breakfast_en-US-JennyNeural_US_female_v2_we_cook_porridge_for_breakfast.mp3'
    },
    {
      id: 'v3',
      word: 'peel',
      ipa: '/piːl/',
      meaning: '\u5265\uff08\u76ae\uff09',
      sentence: 'Let\'s peel the sweet potato.',
      sentenceTranslation: '\u6211\u4eec\u5265\u7ea2\u85af\u5427\u3002',
      audio: '/assets/audio/breakfast/breakfast_en-US-JennyNeural_US_female_v3_lets_peel_the_sweet_potato.mp3'
    }
  ]
};

module.exports = sceneData;
