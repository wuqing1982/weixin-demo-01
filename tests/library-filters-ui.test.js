const assert = require('assert');
const fs = require('fs');
const path = require('path');

const templatePath = path.join(__dirname, '..', 'pages', 'library', 'index.wxml');
const scriptPath = path.join(__dirname, '..', 'pages', 'library', 'index.js');
const servicePath = path.join(__dirname, '..', 'services', 'scene.js');

const template = fs.readFileSync(templatePath, 'utf8');
const script = fs.readFileSync(scriptPath, 'utf8');
const service = fs.readFileSync(servicePath, 'utf8');

assert(
  template.includes('section-heading">场景分类') && template.includes('section-heading">场景合集'),
  'library page should render category and collection filter sections'
);

assert(
  template.includes('data-category-id="{{item.categoryId}}"') && template.includes('data-collection-id="{{item.collectionId}}"'),
  'library page should bind category and collection filter chips'
);

assert(
  script.includes('getSceneCategories') && script.includes('getSceneCollections'),
  'library page should load public scene taxonomy data'
);

assert(
  script.includes('onSelectCategory') && script.includes('onSelectCollection'),
  'library page should expose filter interaction handlers'
);

assert(
  service.includes('function getSceneCategories') && service.includes('function getSceneCollections'),
  'scene service should expose taxonomy request helpers'
);

console.log('library filters ui tests passed');
