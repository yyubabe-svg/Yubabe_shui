import axios from 'axios'

// API 基础地址配置
const getBaseURL = (): string => {
  // @ts-ignore
  if (typeof window !== 'undefined' && window.__API_BASE_URL__) {
    // @ts-ignore
    return window.__API_BASE_URL__
  }
  return '/api'
}

const STORAGE_KEY = 'shushui_user'

const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 120000, // 上传/解析可能需要较长时间
  headers: {
    'Content-Type': 'application/json',
  },
})

// 内存中缓存用户名（防止localStorage被意外清除时仍能传递）
let _cachedUserName: string | null = null

// 设置用户名（登录成功后调用）
export function setUserName(name: string) {
  const trimmedName = name?.trim()
  console.log('[API] setUserName called with:', name, '-> trimmed:', trimmedName)
  if (trimmedName) {
    _cachedUserName = trimmedName
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ name: trimmedName }))
      console.log('[API] User name saved to localStorage:', trimmedName)
    } catch (e) {
      console.error('[API] Failed to save to localStorage:', e)
    }
  }
}

// 清除用户名（退出登录时调用）
export function clearUserName() {
  _cachedUserName = null
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {}
}

// 获取用户名（优先localStorage，其次内存缓存）
function getStoredUserName(): string | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const data = JSON.parse(raw)
      if (data.name && typeof data.name === 'string' && data.name.trim()) {
        _cachedUserName = data.name.trim()
        return _cachedUserName
      }
    }
  } catch {}
  // 确保内存缓存也不是空字符串
  if (_cachedUserName && typeof _cachedUserName === 'string' && _cachedUserName.trim()) {
    return _cachedUserName.trim()
  }
  return null
}

// 请求拦截器：自动添加 X-User-Name 头
api.interceptors.request.use(
  (config) => {
    const name = getStoredUserName()
    console.log('[API] Request interceptor for', config.url, '- user name:', name)
    if (name) {
      config.headers['X-User-Name'] = name
      // 同时添加另一个header名以防代理过滤
      config.headers['X-Username'] = name
      console.log('[API] Headers set, X-User-Name:', name)
    } else {
      console.warn('[API] No user name available for request:', config.url)
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 定义全局事件类型
export type UpgradeEvent = CustomEvent<{ feature?: string; reason?: string }>
export type AuthErrorEvent = CustomEvent<{ reason?: string }>

// 触发全局升级弹窗事件
export function triggerUpgrade(feature?: string, reason?: string) {
  window.dispatchEvent(new CustomEvent('showUpgradeModal', { detail: { feature, reason } }))
}

// 触发认证失败事件（仅用于确实需要重新登录的场景）
export function triggerAuthError(reason?: string) {
  clearUserName()
  window.dispatchEvent(new CustomEvent('authError', { detail: { reason } }))
}

// 响应拦截器 - 统一错误处理
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ERR_NETWORK' || !error.response) {
      console.error('API连接失败，请确保后端服务已启动')
      error.isConnectionError = true
      return Promise.reject(error)
    }

    const status = error.response?.status
    const detail = error.response?.data?.detail
    const url = error.config?.url || ''

    if (status === 401) {
      // 只在明确需要登录的接口返回401时才触发登录页
      // 支付接口401时给出提示即可，不要清除用户状态
      const isAuthEndpoint = url.includes('/usage/register') || url.includes('/usage/status')
      if (isAuthEndpoint) {
        triggerAuthError(detail)
      }
      // 其他接口（如支付）的401只抛出错误，由组件处理，不清除登录状态
    } else if (status === 402) {
      // 需要付费升级
      triggerUpgrade(undefined, detail)
    }

    return Promise.reject(error)
  }
)

export default api
export { STORAGE_KEY }

// ==================== 支付相关API ====================
export interface PlanInfo {
  price: number
  days: number
  name: string
  savings?: string
}

export interface PaymentPlans {
  monthly: PlanInfo
  yearly: PlanInfo
  alipay_enabled: boolean
  manual_payment_enabled: boolean
  manual_payment_qr_url?: string
  manual_payment_note?: string
  admin_wechat?: string
}

export interface CreateOrderResult {
  out_trade_no: string
  pay_url: string  // 跳转到支付宝的URL
  amount: number
  plan_type: string
  duration_days: number
  alipay_enabled: boolean
  manual_payment: boolean
  manual_qr_url?: string
  manual_qr_base64?: string  // base64编码的收款码图片，直接显示
  message: string
}

export interface OrderStatusResult {
  out_trade_no: string
  status: string
  paid: boolean
  activated: boolean
  amount: number
  trade_no?: string
  is_pro: boolean
  pro_expire_at?: string
}

export const paymentApi = {
  // 获取套餐信息
  getPlans: () => api.get<PaymentPlans>('/payment/plans').then(r => r.data),

  // 创建支付订单（在请求体和header中同时传递用户名，确保万无一失）
  createOrder: (planType: 'month' | 'year', userName?: string | null) => {
    const nameToUse = userName?.trim()
    if (nameToUse) {
      // 强制设置用户名到缓存
      setUserName(nameToUse)
    }
    console.log('[Payment API] createOrder with userName:', nameToUse)
    // 请求体中直接包含user_name
    return api.post<CreateOrderResult>('/payment/create-order', { 
      plan_type: planType,
      user_name: nameToUse || undefined,
    }).then(r => r.data)
  },

  // 查询订单状态
  getOrderStatus: (outTradeNo: string, userName?: string | null) => {
    return api.get<OrderStatusResult>(`/payment/order-status/${outTradeNo}`).then(r => r.data)
  },
}
