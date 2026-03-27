// 示例代码 - 包含一些常见问题
var apiKey = 'secret-key-123';
var password = 'user123';

function unsafeFunction(userInput) {
  // 使用 eval - 安全问题
  var result = eval(userInput);
  return result;
}

function renderUserContent(content) {
  // 使用 innerHTML - XSS 风险
  var div = document.createElement('div');
  div.innerHTML = content;
  return div;
}

function logUserInfo(user) {
  // 记录敏感信息
  console.log('User login:', user.name, 'password:', password);
}

function updateElements() {
  // 循环中的 DOM 查询
  var items = document.querySelectorAll('.item');
  for (var i = 0; i < items.length; i++) {
    var element = document.querySelector('.item-' + i);
    if (element) {
      element.textContent = 'Updated';
    }
  }
}

console.log('Example loaded');
