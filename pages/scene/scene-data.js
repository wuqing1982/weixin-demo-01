const sceneData = {
  sceneId: 'beach_picnic',
  title: '海滩野餐',
  background: '/assets/images/beach_picnic.jpg',
  items: [
    {
      id: 'wine_glass',
      word: 'wine glass',
      ipa: '/waɪn ɡlæs/',
      meaning: '红酒杯',
      sentence: 'Look at the wine glasses on the table.',
      sentenceTranslation: '看桌子上的酒杯。',
      rect: { l: 20, t: 40, w: 10, h: 10 },
      audio: '/assets/audio/beach_picnic/beach_picnic_en-US-JennyNeural_US_female_wine_glass_look_at_the_wine_glasses_on.mp3'
    },
    {
      id: 'kombucha_bottle',
      word: 'kombucha bottle',
      ipa: '/ˌkɒmbuːˈtʃɑː bəʊtl/',
      meaning: '康普茶瓶子',
      sentence: 'There are two kombucha bottles next to each other.',
      sentenceTranslation: '有两个康普茶瓶子并排着。',
      rect: { l: 30, t: 45, w: 10, h: 10 },
      audio: '/assets/audio/beach_picnic/beach_picnic_en-US-JennyNeural_US_female_kombucha_bottle_there_are_two_kombucha_bottles_next.mp3'
    },
    {
      id: 'cake',
      word: 'cake',
      ipa: '/keɪk/',
      meaning: '蛋糕',
      sentence: 'The cake is shaped like a bear.',
      sentenceTranslation: '这个蛋糕像一只熊。',
      rect: { l: 50, t: 55, w: 10, h: 10 },
      audio: '/assets/audio/beach_picnic/beach_picnic_en-US-JennyNeural_US_female_cake_the_cake_is_shaped_like_a.mp3'
    },
    {
      id: 'basket',
      word: 'basket',
      ipa: '/bæskɪt/',
      meaning: '篮子',
      sentence: 'The basket is filled with flowers.',
      sentenceTranslation: '篮子里装满了花。',
      rect: { l: 10, t: 60, w: 10, h: 10 },
      audio: '/assets/audio/beach_picnic/beach_picnic_en-US-JennyNeural_US_female_basket_the_basket_is_filled_with_flowers.mp3'
    }
  ],
  verbs: []
};

module.exports = sceneData;
