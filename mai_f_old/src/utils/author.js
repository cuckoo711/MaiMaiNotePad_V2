export const getAuthorName = (item) => {
  if (!item) {
    return '用户已注销'
  }
  if (item.uploader_name) {
    return item.uploader_name
  }
  if (item.author) {
    return item.author
  }
  if (item.author_id) {
    return item.author_id
  }
  if (item.uploader_id) {
    return item.uploader_id
  }
  return '用户已注销'
}

export const getAuthorDisplay = (item) => {
  const name = getAuthorName(item)
  return name ? `作者: ${name}` : '作者: 用户已注销'
}
