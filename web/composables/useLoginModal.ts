/** 登录弹窗全局状态：手机验证码 / GitHub / Gitee 三 Tab。 */
export const useLoginModal = () => {
  const isOpen = useState<boolean>('login-modal-open', () => false)
  const open = () => { isOpen.value = true }
  const close = () => { isOpen.value = false }
  return { isOpen, open, close }
}
