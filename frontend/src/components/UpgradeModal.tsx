import React, { useState, useEffect, useCallback, useRef } from 'react'
import { X, Zap, Check, AlertCircle, Loader2, CreditCard, ExternalLink } from 'lucide-react'
import { paymentApi, type PaymentPlans, type CreateOrderResult } from '../api/client'
import { useAuth } from '../context/AuthContext'

interface UpgradeModalProps {
  isOpen: boolean
  onClose: () => void
  feature?: string
  reason?: string
}

export default function UpgradeModal({ isOpen, onClose, feature, reason }: UpgradeModalProps) {
  const { refreshProStatus, userName, user } = useAuth()
  const [plans, setPlans] = useState<PaymentPlans | null>(null)
  const [selectedPlan, setSelectedPlan] = useState<'month' | 'year'>('year')
  const [loading, setLoading] = useState(false)
  const [orderResult, setOrderResult] = useState<CreateOrderResult | null>(null)
  const [paymentStatus, setPaymentStatus] = useState<'idle' | 'pending' | 'success' | 'failed'>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [checkingPayment, setCheckingPayment] = useState(false)
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 加载套餐信息
  useEffect(() => {
    if (isOpen) {
      paymentApi.getPlans().then(setPlans).catch(err => {
        setErrorMsg('加载套餐信息失败')
      })
      setOrderResult(null)
      setPaymentStatus('idle')
      setErrorMsg('')
    }
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
      }
    }
  }, [isOpen])

  // 轮询订单状态
  const pollOrderStatus = useCallback((outTradeNo: string, currentUserName: string) => {
    if (pollTimerRef.current) clearInterval(pollTimerRef.current)
    
    let attempts = 0
    pollTimerRef.current = setInterval(async () => {
      attempts++
      try {
        const status = await paymentApi.getOrderStatus(outTradeNo, currentUserName)
        if (status.paid && status.activated) {
          clearInterval(pollTimerRef.current!)
          setPaymentStatus('success')
          setCheckingPayment(false)
          await refreshProStatus()
        }
        // 最多轮询5分钟（150次 * 2秒）
        if (attempts > 150) {
          clearInterval(pollTimerRef.current!)
          setCheckingPayment(false)
        }
      } catch (e) {
        console.error('查询订单状态失败', e)
      }
    }, 2000)
  }, [refreshProStatus])

  // 创建订单并显示收款码
  const handlePay = async () => {
    // 优先从user状态获取用户名（最可靠）
    const currentUserName = user?.name || userName
    console.log('[UpgradeModal] handlePay, user:', user, 'userName:', userName, 'currentUserName:', currentUserName)
    
    // 先检查是否已登录
    if (!currentUserName || !currentUserName.trim()) {
      setErrorMsg('请先登录（输入姓名）后再进行支付')
      return
    }
    
    const finalUserName = currentUserName.trim()
    setLoading(true)
    setErrorMsg('')
    try {
      const result = await paymentApi.createOrder(selectedPlan, finalUserName)
      console.log('[Payment] Order created:', result)
      setOrderResult(result)
      
      if (result.manual_payment) {
        // 个人收款码模式：直接显示二维码，不跳转
        setPaymentStatus('pending')
        setLoading(false)
        return
      }
      
      // 支付宝在线支付：跳转到支付页面
      setPaymentStatus('pending')
      setCheckingPayment(true)
      setLoading(false)
      
      // 在新窗口打开支付宝支付页面
      const payWindow = window.open(result.pay_url, '_blank')
      
      // 开始轮询支付状态
      pollOrderStatus(result.out_trade_no, finalUserName)
      
      // 如果弹窗被拦截，提示用户
      if (!payWindow) {
        setErrorMsg('弹窗被浏览器拦截，请点击下方按钮手动打开支付页面')
      }
    } catch (err: any) {
      console.error('[Payment] Create order failed:', err)
      setErrorMsg(err.response?.data?.detail || '创建订单失败，请重试')
      setPaymentStatus('failed')
      setLoading(false)
    }
  }

  // 手动打开支付页面
  const openPayPage = () => {
    if (orderResult) {
      window.open(orderResult.pay_url, '_blank')
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
        {/* 头部 */}
        <div className="relative bg-gradient-to-r from-blue-600 to-cyan-600 p-6 text-white rounded-t-2xl">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1 hover:bg-white/20 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-3">
            <div className="bg-white/20 p-2 rounded-xl">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold">升级 Pro 专业版</h2>
              <p className="text-blue-100 text-sm mt-0.5">解锁全部高级功能</p>
            </div>
          </div>
          {feature && (
            <p className="mt-3 bg-white/10 rounded-lg px-3 py-2 text-sm">
              💡 {reason || `"${feature}" 功能需要 Pro 版本`}
            </p>
          )}
        </div>

        <div className="p-6">
          {/* 成功状态 */}
          {paymentStatus === 'success' ? (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="w-8 h-8 text-green-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">🎉 支付成功！</h3>
              <p className="text-gray-600 mb-6">
                Pro 专业版已激活，有效期至 {new Date(Date.now() + (orderResult?.duration_days || 30) * 86400000).toLocaleDateString('zh-CN')}
              </p>
              <button
                onClick={onClose}
                className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white px-8 py-3 rounded-xl font-medium hover:shadow-lg transition-all"
              >
                开始使用
              </button>
            </div>
          ) : paymentStatus === 'pending' && orderResult ? (
            /* 支付中状态 */
            <div className="text-center py-4">
              <div className="mb-4">
                <h3 className="text-lg font-semibold text-gray-900 mb-1">
                  {orderResult.manual_payment ? '支付宝扫码支付' : '正在等待支付'}
                </h3>
                <p className="text-gray-500 text-sm">{orderResult.message}</p>
              </div>

              {/* 支付宝在线支付 - 等待支付 */}
              {!orderResult.manual_payment && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-4">
                  {checkingPayment ? (
                    <>
                      <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-3" />
                      <p className="text-sm text-blue-700 mb-3">
                        已打开支付宝支付页面，请在新窗口中完成支付
                      </p>
                      <p className="text-xs text-blue-500 mb-4">
                        支付完成后系统将自动确认，请勿关闭此页面
                      </p>
                    </>
                  ) : (
                    <p className="text-sm text-blue-700 mb-3">支付页面已打开，请完成支付</p>
                  )}
                  <button
                    onClick={openPayPage}
                    className="inline-flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm"
                  >
                    <ExternalLink className="w-4 h-4" />
                    重新打开支付页面
                  </button>
                </div>
              )}

              {/* 个人收款码模式 - 显示二维码 */}
              {orderResult.manual_payment && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 mb-4">
                  <div className="text-center">
                    <AlertCircle className="w-6 h-6 text-yellow-600 mx-auto mb-2" />
                    <p className="font-medium text-yellow-800 mb-3">请使用支付宝扫码转账</p>
                    <div className="w-56 h-56 mx-auto bg-white border-2 border-yellow-300 rounded-xl flex items-center justify-center p-2 shadow-md">
                      <img
                        src={orderResult.manual_qr_base64 || orderResult.manual_qr_url || '/qrcodes/alipay.png'}
                        alt="支付宝收款码"
                        className="w-full h-full object-contain"
                        onLoad={() => console.log('[Payment] QR code loaded successfully')}
                        onError={(e) => {
                          console.error('[Payment] QR code failed to load, src:', (e.target as HTMLImageElement).src)
                          ;(e.target as HTMLImageElement).style.display = 'none'
                          const parent = (e.target as HTMLImageElement).parentElement
                          if (parent) {
                            parent.innerHTML = '<div class="text-gray-400 text-sm text-center px-4"><p>收款码加载失败</p><p class="text-xs mt-1">请刷新页面重试或联系管理员</p></div>'
                          }
                        }}
                      />
                    </div>
                    <p className="text-yellow-800 text-xl font-bold mt-4">
                      转账金额：¥{orderResult.amount}
                    </p>
                    <div className="mt-3 text-sm text-yellow-700 space-y-1">
                      <p>转账后请添加管理员微信：</p>
                      <p className="font-mono font-bold text-yellow-900 text-lg">{plans?.admin_wechat || '130******78'}</p>
                      <p className="mt-2">发送<span className="font-bold">转账截图</span>和您的用户名</p>
                      <p className="font-bold text-yellow-900">「{userName || '未获取到用户名'}」</p>
                      <p>确认后将立即为您激活Pro</p>
                    </div>
                  </div>
                </div>
              )}

              <button
                onClick={() => {
                  setOrderResult(null)
                  setPaymentStatus('idle')
                  setCheckingPayment(false)
                  if (pollTimerRef.current) clearInterval(pollTimerRef.current)
                }}
                className="text-gray-500 text-sm hover:text-gray-700"
              >
                ← 返回选择套餐
              </button>
            </div>
          ) : (
            /* 套餐选择 */
            <>
              {/* 功能列表 */}
              <div className="bg-gray-50 rounded-xl p-4 mb-5">
                <h3 className="font-semibold text-gray-900 mb-3">Pro 专业版权益</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {[
                    '上传 50MB 大文件',
                    '500MB 总存储空间',
                    '无限次 AI 问答',
                    'ISO 体系文件生成',
                    '优先客服支持',
                    '更多高级功能',
                  ].map((item) => (
                    <div key={item} className="flex items-center gap-2 text-gray-700">
                      <Check className="w-4 h-4 text-green-500 flex-shrink-0" />
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 支付方式说明 */}
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-4 flex items-start gap-2">
                <CreditCard className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-green-700">
                  <p className="font-medium">支付宝个人收款码支付</p>
                  <p className="text-xs mt-0.5">点击支付后显示收款二维码，使用支付宝扫码转账</p>
                </div>
              </div>

              {/* 套餐选择 */}
              <div className="space-y-3 mb-5">
                {plans && (
                  <>
                    <button
                      onClick={() => setSelectedPlan('year')}
                      className={`w-full p-4 rounded-xl border-2 transition-all text-left ${
                        selectedPlan === 'year'
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold">Pro 年卡</span>
                            <span className="bg-orange-100 text-orange-600 text-xs px-2 py-0.5 rounded-full font-medium">
                              超值
                            </span>
                          </div>
                          <p className="text-sm text-gray-500 mt-0.5">365天，平均每天仅 ¥{(plans.yearly.price / 365).toFixed(2)}</p>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-gray-900">¥{plans.yearly.price}</div>
                          {plans.yearly.savings && (
                            <div className="text-xs text-orange-600">{plans.yearly.savings}</div>
                          )}
                        </div>
                      </div>
                    </button>

                    <button
                      onClick={() => setSelectedPlan('month')}
                      className={`w-full p-4 rounded-xl border-2 transition-all text-left ${
                        selectedPlan === 'month'
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <span className="font-semibold">Pro 月卡</span>
                          <p className="text-sm text-gray-500 mt-0.5">30天，灵活选择</p>
                        </div>
                        <div className="text-2xl font-bold text-gray-900">¥{plans.monthly.price}</div>
                      </div>
                    </button>
                  </>
                )}
              </div>

              {/* 错误提示 */}
              {errorMsg && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-red-700">{errorMsg}</p>
                </div>
              )}

              {/* 支付按钮 */}
              <button
                onClick={handlePay}
                disabled={loading}
                className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 text-white py-3.5 rounded-xl font-medium hover:shadow-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    处理中...
                  </>
                ) : (
                  <>
                    <CreditCard className="w-5 h-5" />
                    立即支付 ¥{selectedPlan === 'year' ? (plans?.yearly.price || 99) : (plans?.monthly.price || 29)}
                  </>
                )}
              </button>

              <p className="text-center text-xs text-gray-400 mt-3">
                支付即表示同意服务条款 · 支付宝扫码支付
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
