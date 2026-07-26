import React, { useState, useEffect, useRef, useCallback } from 'react'

function getCookie(name) {
  const value = `; ${document.cookie}`
  const parts = value.split(`; ${name}=`)
  if (parts.length === 2) return parts.pop().split(';').shift()
  return ''
}

async function apiPost(url, data = {}) {
  const formData = new URLSearchParams()
  Object.entries(data).forEach(([k, v]) => formData.append(k, v))
  const res = await fetch(url, {
    method: 'POST', credentials: 'include',
    headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
    body: formData,
  })
  if (res.headers.get('content-type')?.includes('application/json')) return res.json()
  return { status: 'redirect' }
}

function nepaliNumber(n) {
  const s = parseFloat(n).toFixed(2)
  const parts = s.split('.')
  let intPart = parts[0]
  const decPart = parts[1]
  let isNeg = false
  if (intPart.startsWith('-')) { isNeg = true; intPart = intPart.slice(1) }
  let result = ''
  const len = intPart.length
  if (len <= 3) { result = intPart }
  else {
    result = intPart.slice(-3)
    let remaining = intPart.slice(0, -3)
    while (remaining.length > 2) {
      result = remaining.slice(-2) + ',' + result
      remaining = remaining.slice(0, -2)
    }
    if (remaining.length > 0) result = remaining + ',' + result
  }
  return (isNeg ? '-' : '') + result + '.' + decPart
}

const CAT_ICONS = {
  'all': 'fa-solid fa-grip',
  'phone': 'fa-solid fa-mobile-screen',
  'laptop': 'fa-solid fa-laptop',
  'earbuds': 'fa-solid fa-headphones',
  'watch': 'fa-solid fa-clock',
  'accessories': 'fa-solid fa-plug',
  'electronics': 'fa-solid fa-microchip',
  'clothing': 'fa-solid fa-shirt',
  'food': 'fa-solid fa-utensils',
  'other': 'fa-solid fa-box',
}

function getCategoryIcon(name) {
  const n = name.toLowerCase()
  for (const [key, icon] of Object.entries(CAT_ICONS)) {
    if (n.includes(key)) return icon
  }
  return 'fa-solid fa-tag'
}

function Toast({ message, type = 'success', onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t) }, [])
  const bg = type === 'error' ? '#ef4444' : type === 'warning' ? '#f59e0b' : '#10b981'
  return (
    <div style={{
      position: 'fixed', top: 20, right: 20, zIndex: 9999,
      background: bg, color: '#fff', padding: '14px 24px',
      borderRadius: 12, boxShadow: `0 12px 40px ${bg}44`,
      animation: 'posSlideIn 0.3s ease', fontSize: 14, fontWeight: 600,
      display: 'flex', alignItems: 'center', gap: 10, maxWidth: 400,
    }}>
      <i className={type === 'error' ? 'fa-solid fa-circle-xmark' : type === 'warning' ? 'fa-solid fa-triangle-exclamation' : 'fa-solid fa-circle-check'}></i>
      <span>{message}</span>
      <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', fontSize: 18, lineHeight: 1, marginLeft: 'auto' }}>&times;</button>
    </div>
  )
}

function SearchBar({ onSearch, query, setQuery, onClear }) {
  const inputRef = useRef(null)

  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); inputRef.current?.focus() }
      if (e.key === 'Escape') { setQuery(''); onClear?.(); inputRef.current?.blur() }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  return (
    <div style={{
      position: 'relative', width: '100%',
    }}>
      <div style={{ position: 'relative' }}>
        <i className="fa-solid fa-magnifying-glass" style={{
          position: 'absolute', left: 16, top: '50%', transform: 'translateY(-50%)',
          fontSize: 16, color: '#94a3b8', pointerEvents: 'none',
        }}></i>
        <input
          ref={inputRef} type="text" value={query}
          onChange={e => { setQuery(e.target.value); onSearch(e.target.value) }}
          placeholder="Search products..."
          style={{
            width: '100%', padding: '14px 100px 14px 46px',
            border: '2px solid #e2e8f0', borderRadius: 12, fontSize: 15,
            outline: 'none', transition: 'all 0.2s', boxSizing: 'border-box',
            background: '#fff', color: '#1e293b', fontWeight: 500,
          }}
          onFocus={e => { e.target.style.borderColor = '#3b82f6'; e.target.style.boxShadow = '0 0 0 4px rgba(59,130,246,0.1)' }}
          onBlur={e => { e.target.style.borderColor = '#e2e8f0'; e.target.style.boxShadow = 'none' }}
        />
        {query && (
          <button onClick={() => { setQuery(''); onClear?.(); inputRef.current?.focus() }} style={{
            position: 'absolute', right: 14, top: '50%', transform: 'translateY(-50%)',
            background: '#f1f5f9', border: 'none', borderRadius: 8, width: 28, height: 28,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: '#64748b', fontSize: 14,
          }}><i className="fa-solid fa-xmark"></i></button>
        )}
        <span style={{
          position: 'absolute', right: query ? 50 : 14, top: '50%', transform: 'translateY(-50%)',
          background: '#f1f5f9', border: '1px solid #e2e8f0', borderRadius: 6,
          padding: '2px 8px', fontSize: 11, color: '#94a3b8', fontWeight: 500,
        }}>
          <i className="fa-solid fa-keyboard" style={{ marginRight: 4 }}></i>Ctrl+K
        </span>
      </div>
    </div>
  )
}

function CategoryBar({ categories, selected, onSelect }) {
  const scrollRef = useRef(null)
  return (
    <div ref={scrollRef} style={{
      display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4,
      scrollbarWidth: 'none', msOverflowStyle: 'none',
      WebkitOverflowScrolling: 'touch',
    }}>
      <button onClick={() => onSelect(null)} style={{
        flexShrink: 0, padding: '10px 18px', borderRadius: 10, border: '2px solid',
        borderColor: selected === null ? '#3b82f6' : '#e2e8f0',
        background: selected === null ? '#3b82f6' : '#fff',
        color: selected === null ? '#fff' : '#475569',
        fontSize: 13, fontWeight: 600, cursor: 'pointer',
        display: 'flex', alignItems: 'center', gap: 8,
        transition: 'all 0.2s', whiteSpace: 'nowrap',
      }}>
        <i className="fa-solid fa-grip"></i> All
      </button>
      {categories.map(cat => (
        <button key={cat.id} onClick={() => onSelect(cat.id)} style={{
          flexShrink: 0, padding: '10px 18px', borderRadius: 10, border: '2px solid',
          borderColor: selected === cat.id ? '#3b82f6' : '#e2e8f0',
          background: selected === cat.id ? '#3b82f6' : '#fff',
          color: selected === cat.id ? '#fff' : '#475569',
          fontSize: 13, fontWeight: 600, cursor: 'pointer',
          display: 'flex', alignItems: 'center', gap: 8,
          transition: 'all 0.2s', whiteSpace: 'nowrap',
        }}>
          <i className={getCategoryIcon(cat.name)}></i> {cat.name}
          <span style={{
            background: selected === cat.id ? 'rgba(255,255,255,0.2)' : '#f1f5f9',
            padding: '1px 8px', borderRadius: 12, fontSize: 11,
          }}>{cat.count}</span>
        </button>
      ))}
    </div>
  )
}

function ProductCard({ product, onAdd, cartQty }) {
  const [hovered, setHovered] = useState(false)
  const outOfStock = product.stock <= 0
  const lowStock = product.stock > 0 && product.stock <= 5

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      onClick={() => !outOfStock && onAdd(product)}
      style={{
        background: '#fff', borderRadius: 14, border: '1px solid #f1f5f9',
        overflow: 'hidden', cursor: outOfStock ? 'not-allowed' : 'pointer',
        transition: 'all 0.2s ease', opacity: outOfStock ? 0.6 : 1,
        boxShadow: hovered && !outOfStock ? '0 8px 30px rgba(0,0,0,0.08)' : '0 1px 3px rgba(0,0,0,0.04)',
        transform: hovered && !outOfStock ? 'translateY(-2px)' : 'none',
      }}
    >
      <div style={{
        height: 140, background: '#f8fafc', display: 'flex', alignItems: 'center', justifyContent: 'center',
        position: 'relative', overflow: 'hidden',
      }}>
        {product.image ? (
          <img src={product.image} alt={product.name} style={{
            width: '100%', height: '100%', objectFit: 'cover',
          }} />
        ) : (
          <i className="fa-solid fa-box-open" style={{ fontSize: 42, color: '#cbd5e1' }}></i>
        )}
        {cartQty > 0 && (
          <div style={{
            position: 'absolute', top: 8, right: 8,
            background: '#3b82f6', color: '#fff', borderRadius: 8,
            padding: '3px 10px', fontSize: 12, fontWeight: 700,
            boxShadow: '0 2px 8px rgba(59,130,246,0.3)',
          }}>
            {cartQty} in cart
          </div>
        )}
        {outOfStock && (
          <div style={{
            position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#fff', fontSize: 13, fontWeight: 700, letterSpacing: 1,
          }}>OUT OF STOCK</div>
        )}
      </div>
      <div style={{ padding: '12px 14px' }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: '#1e293b', marginBottom: 2, lineHeight: 1.3, minHeight: 34,
          display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
          {product.name}
        </div>
        <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 8 }}>{product.sku}</div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: 17, fontWeight: 800, color: '#1e293b' }}>
            रू {nepaliNumber(product.price)}
          </span>
          {lowStock && (
            <span style={{
              fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 6,
              background: '#fef3c7', color: '#d97706',
            }}>Low: {product.stock}</span>
          )}
        </div>
        {!outOfStock && (
          <div style={{ fontSize: 11, color: '#10b981', fontWeight: 500, marginTop: 4 }}>
            <i className="fa-solid fa-check-circle" style={{ marginRight: 4 }}></i>
            {product.stock} in stock
          </div>
        )}
      </div>
    </div>
  )
}

function CartItem({ item, onRemove, onUpdate }) {
  const [qty, setQty] = useState(item.quantity)

  function handleQtyChange(newQty) {
    if (newQty < 1) { onRemove(item.id); return }
    setQty(newQty)
    onUpdate(item.id, newQty)
  }

  useEffect(() => { setQty(item.quantity) }, [item.quantity])

  const lineTotal = item.quantity * parseFloat(item.unit_price)

  return (
    <div style={{
      padding: '12px 14px', background: '#fff', borderRadius: 12, marginBottom: 6,
      border: '1px solid #f1f5f9', transition: 'all 0.15s',
      animation: 'posFadeIn 0.2s ease',
    }}>
      <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
        {item.image ? (
          <img src={item.image} alt={item.product_name} style={{
            width: 48, height: 48, borderRadius: 10, objectFit: 'cover',
            border: '1px solid #e2e8f0', flexShrink: 0,
          }} />
        ) : (
          <div style={{
            width: 48, height: 48, borderRadius: 10, background: '#f1f5f9',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, border: '1px solid #e2e8f0',
          }}>
            <i className="fa-solid fa-box-open" style={{ fontSize: 18, color: '#cbd5e1' }}></i>
          </div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 13, color: '#1e293b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', lineHeight: 1.3 }}>
            {item.product_name}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3, flexWrap: 'wrap' }}>
            {item.sku && (
              <span style={{ fontSize: 10, fontWeight: 600, color: '#64748b', background: '#f1f5f9', padding: '1px 6px', borderRadius: 4 }}>
                {item.sku}
              </span>
            )}
            {item.category && (
              <span style={{ fontSize: 10, fontWeight: 600, color: '#7c3aed', background: '#f3f0ff', padding: '1px 6px', borderRadius: 4 }}>
                <i className="fa-solid fa-tag" style={{ fontSize: 8, marginRight: 2 }}></i>{item.category}
              </span>
            )}
          </div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
            रू {nepaliNumber(item.unit_price)} × {item.quantity}
          </div>
        </div>
        <button
          onClick={() => onRemove(item.id)}
          style={{
            width: 26, height: 26, borderRadius: 6, border: 'none',
            background: 'transparent', cursor: 'pointer',
            color: '#94a3b8', display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.15s', flexShrink: 0, alignSelf: 'flex-start',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = '#fef2f2'; e.currentTarget.style.color = '#ef4444' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#94a3b8' }}
          title="Remove item"
        >
          <i className="fa-solid fa-xmark" style={{ fontSize: 12 }}></i>
        </button>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0', overflow: 'hidden' }}>
          <button
            onClick={() => handleQtyChange(qty - 1)}
            style={{
              width: 30, height: 30, border: 'none', borderRight: '1px solid #e2e8f0',
              background: 'transparent', cursor: 'pointer', fontSize: 14, fontWeight: 700,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: qty <= 1 ? '#ef4444' : '#3b82f6', transition: 'all 0.15s',
            }}
          >
            <i className={qty <= 1 ? 'fa-solid fa-trash-can' : 'fa-solid fa-minus'} style={{ fontSize: 11 }}></i>
          </button>
          <input
            type="number" value={qty}
            onChange={e => handleQtyChange(parseInt(e.target.value) || 1)}
            style={{
              width: 36, textAlign: 'center', padding: '4px 0',
              border: 'none', background: 'transparent', fontSize: 14,
              fontWeight: 700, outline: 'none', color: '#1e293b',
              MozAppearance: 'textfield',
            }}
          />
          <button
            onClick={() => handleQtyChange(qty + 1)}
            style={{
              width: 30, height: 30, border: 'none', borderLeft: '1px solid #e2e8f0',
              background: 'transparent', cursor: 'pointer', fontSize: 14, fontWeight: 700,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#3b82f6', transition: 'all 0.15s',
            }}
          >
            <i className="fa-solid fa-plus" style={{ fontSize: 11 }}></i>
          </button>
        </div>
        <div style={{ fontWeight: 800, fontSize: 14, color: '#1e293b' }}>
          रू {nepaliNumber(lineTotal)}
        </div>
      </div>
    </div>
  )
}

function PaymentModal({ cart, paymentMethod, setPaymentMethod, amountTendered, setAmountTendered, onComplete, completing, onKhaltiPay, khaltiLoading, onClose }) {
  const methods = [
    { key: 'Cash', icon: 'fa-solid fa-money-bill-wave', label: 'Cash' },
    { key: 'Card', icon: 'fa-solid fa-credit-card', label: 'Card' },
    { key: 'Mobile Wallet', icon: 'fa-solid fa-mobile-screen', label: 'Mobile' },
    { key: 'Bank Transfer', icon: 'fa-solid fa-building-columns', label: 'Bank' },
    { key: 'Khalti', icon: 'fa-solid fa-wallet', label: 'Khalti' },
  ]
  const isKhalti = paymentMethod === 'Khalti'
  const change = amountTendered && parseFloat(amountTendered) >= cart.total
    ? (parseFloat(amountTendered) - cart.total).toFixed(2) : null

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9000,
      backdropFilter: 'blur(4px)',
    }} onClick={onClose}>
      <div style={{
        background: '#fff', borderRadius: 20, padding: 32, width: '100%', maxWidth: 420,
        boxShadow: '0 24px 80px rgba(0,0,0,0.15)',
        animation: 'posFadeIn 0.2s ease',
      }} onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h2 style={{ fontSize: 20, fontWeight: 800, color: '#1e293b', margin: 0 }}>
            <i className="fa-solid fa-credit-card" style={{ marginRight: 10, color: '#3b82f6' }}></i>
            Payment
          </h2>
          <button onClick={onClose} style={{ background: '#f1f5f9', border: 'none', borderRadius: 8, width: 32, height: 32, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div style={{ background: '#f8fafc', borderRadius: 12, padding: '16px 20px', marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 14, color: '#64748b' }}>Amount Due</span>
          <span style={{ fontSize: 28, fontWeight: 900, color: '#1e293b' }}>रू {nepaliNumber(cart.total)}</span>
        </div>

        <div style={{ marginBottom: 20 }}>
          <label style={{ fontSize: 12, fontWeight: 700, color: '#475569', display: 'block', marginBottom: 10, textTransform: 'uppercase', letterSpacing: 0.5 }}>Payment Method</label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {methods.map(m => (
              <button key={m.key} onClick={() => setPaymentMethod(m.key)} style={{
                padding: '12px 8px', border: `2px solid ${paymentMethod === m.key ? '#3b82f6' : '#e2e8f0'}`,
                borderRadius: 10, fontSize: 12, fontWeight: 600, cursor: 'pointer',
                background: paymentMethod === m.key ? '#eff6ff' : '#fff',
                color: paymentMethod === m.key ? '#3b82f6' : '#64748b',
                transition: 'all 0.2s', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6,
              }}>
                <i className={m.icon} style={{ fontSize: 20 }}></i>
                <span>{m.label}</span>
              </button>
            ))}
          </div>
        </div>

        {!isKhalti && (
          <div style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 12, fontWeight: 700, color: '#475569', display: 'block', marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.5 }}>Amount Tendered</label>
            <input
              type="number" step="0.01" min={cart.total}
              value={amountTendered}
              onChange={e => setAmountTendered(e.target.value)}
              placeholder={`Min: रू ${nepaliNumber(cart.total)}`}
              autoFocus
              style={{
                width: '100%', padding: '14px 16px', border: '2px solid #e2e8f0',
                borderRadius: 10, fontSize: 18, fontWeight: 700, outline: 'none',
                boxSizing: 'border-box', background: '#f8fafc', color: '#1e293b',
                transition: 'border-color 0.2s',
              }}
              onFocus={e => e.target.style.borderColor = '#3b82f6'}
              onBlur={e => e.target.style.borderColor = '#e2e8f0'}
            />
            {change && (
              <div style={{
                marginTop: 10, padding: '12px 16px', borderRadius: 10, fontSize: 15, fontWeight: 700,
                background: '#ecfdf5', color: '#059669',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              }}>
                <span>Change</span>
                <span style={{ fontSize: 20 }}>रू {change}</span>
              </div>
            )}
          </div>
        )}

        {isKhalti && (
          <div style={{
            marginBottom: 20, padding: '12px 16px', borderRadius: 10, fontSize: 13,
            background: '#f5f3ff', color: '#6d28d9', display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <i className="fa-solid fa-circle-info"></i>
            You'll be redirected to Khalti to complete this payment.
          </div>
        )}

        <button
          onClick={isKhalti ? onKhaltiPay : onComplete}
          disabled={isKhalti ? khaltiLoading : completing}
          style={{
            width: '100%', padding: '16px', border: 'none', borderRadius: 12,
            background: (isKhalti ? khaltiLoading : completing)
              ? '#94a3b8'
              : (isKhalti ? 'linear-gradient(135deg, #5c2d91, #7c3aed)' : 'linear-gradient(135deg, #10b981, #059669)'),
            color: '#fff', fontSize: 16, fontWeight: 700,
            cursor: (isKhalti ? khaltiLoading : completing) ? 'not-allowed' : 'pointer',
            boxShadow: (isKhalti ? khaltiLoading : completing) ? 'none' : '0 6px 20px rgba(16,185,129,0.35)',
            transition: 'all 0.25s', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10,
          }}
        >
          {isKhalti ? (
            khaltiLoading ? (
              <><i className="fa-solid fa-spinner fa-spin"></i> Redirecting to Khalti...</>
            ) : (
              <><i className="fa-solid fa-wallet"></i> Pay with Khalti — रू {nepaliNumber(cart.total)}</>
            )
          ) : completing ? (
            <><i className="fa-solid fa-spinner fa-spin"></i> Processing...</>
          ) : (
            <><i className="fa-solid fa-circle-check"></i> Complete Sale — रू {nepaliNumber(cart.total)}</>
          )}
        </button>
      </div>
    </div>
  )
}

function MobileCartDrawer({ cart, items, onRemove, onUpdate, onPayment, onClose }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 8000,
      backdropFilter: 'blur(4px)',
    }} onClick={onClose}>
      <div style={{
        position: 'absolute', bottom: 0, left: 0, right: 0,
        background: '#fff', borderRadius: '20px 20px 0 0',
        maxHeight: '85vh', overflow: 'hidden', display: 'flex', flexDirection: 'column',
        animation: 'posSlideUp 0.3s ease',
      }} onClick={e => e.stopPropagation()}>
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid #f1f5f9',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: '#f8fafc', borderRadius: '20px 20px 0 0',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <i className="fa-solid fa-cart-shopping" style={{ color: '#3b82f6', fontSize: 18 }}></i>
            <span style={{ fontWeight: 700, fontSize: 16, color: '#1e293b' }}>Cart ({cart.count})</span>
          </div>
          <button onClick={onClose} style={{ background: '#f1f5f9', border: 'none', borderRadius: 8, width: 32, height: 32, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
            <i className="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>
          {items.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>
              <i className="fa-solid fa-cart-shopping" style={{ fontSize: 40, marginBottom: 12, display: 'block', opacity: 0.3 }}></i>
              <p style={{ fontSize: 14, fontWeight: 500 }}>Cart is empty</p>
            </div>
          ) : items.map(item => (
            <CartItem key={item.id} item={item} onRemove={onRemove} onUpdate={onUpdate} />
          ))}
        </div>
        <div style={{ padding: '16px 20px', borderTop: '1px solid #f1f5f9', background: '#f8fafc' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
            <span style={{ color: '#64748b' }}>Subtotal</span>
            <span style={{ fontWeight: 600 }}>रू {nepaliNumber(cart.subtotal)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10, fontSize: 13 }}>
            <span style={{ color: '#64748b' }}>Tax</span>
            <span style={{ fontWeight: 600 }}>रू {nepaliNumber(cart.tax)}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16, paddingBottom: 12, borderBottom: '2px solid #e2e8f0' }}>
            <span style={{ fontWeight: 800, fontSize: 15, color: '#1e293b' }}>Total</span>
            <span style={{ fontWeight: 900, fontSize: 22, color: '#3b82f6' }}>रू {nepaliNumber(cart.total)}</span>
          </div>
          <button
            onClick={() => { onClose(); onPayment() }}
            disabled={items.length === 0}
            style={{
              width: '100%', padding: '16px', border: 'none', borderRadius: 12,
              background: items.length === 0 ? '#94a3b8' : 'linear-gradient(135deg, #3b82f6, #2563eb)',
              color: '#fff', fontSize: 16, fontWeight: 700, cursor: items.length === 0 ? 'not-allowed' : 'pointer',
              boxShadow: items.length === 0 ? 'none' : '0 6px 20px rgba(59,130,246,0.35)',
            }}
          >
            <i className="fa-solid fa-credit-card" style={{ marginRight: 8 }}></i>
            Proceed to Payment
          </button>
        </div>
      </div>
    </div>
  )
}

export default function POSApp() {
  const [cart, setCart] = useState({ lines: [], subtotal: 0, tax: 0, total: 0, count: 0 })
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [completing, setCompleting] = useState(false)
  const [khaltiLoading, setKhaltiLoading] = useState(false)
  const [paymentMethod, setPaymentMethod] = useState('Cash')
  const [amountTendered, setAmountTendered] = useState('')
  const [toast, setToast] = useState(null)
  const [transactionId, setTransactionId] = useState(null)
  const [showPayment, setShowPayment] = useState(false)
  const [showMobileCart, setShowMobileCart] = useState(false)
  const debounceRef = useRef(null)

  const cartApiUrl = '/sales/cart/api/'
  const cartAddUrl = '/sales/cart/add/'
  const cartRemoveBase = '/sales/cart/remove/'
  const cartUpdateBase = '/sales/cart/update/'
  const posProductsUrl = '/api/pos/products/'
  const posCategoriesUrl = '/api/pos/categories/'

  useEffect(() => { loadCart(); loadCategories(); loadProducts() }, [])

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      loadProducts(searchQuery, selectedCategory)
    }, 200)
    return () => clearTimeout(debounceRef.current)
  }, [searchQuery, selectedCategory])

  async function loadCart() {
    try {
      const res = await fetch(cartApiUrl, {
        credentials: 'include',
        headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' }
      })
      if (!res.ok) throw new Error('Failed to load cart')
      const data = await res.json()
      setTransactionId(data.transaction_id)
      setCart({
        lines: data.lines || [],
        total: parseFloat(data.total || 0),
        subtotal: parseFloat(data.subtotal || 0),
        tax: parseFloat(data.tax || 0),
        count: data.count || 0,
      })
    } catch (e) { console.error('Cart load error:', e) }
    setLoading(false)
  }

  async function loadCategories() {
    try {
      const res = await fetch(posCategoriesUrl, { credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') } })
      if (res.ok) setCategories(await res.json())
    } catch (e) { console.error(e) }
  }

  async function loadProducts(q, catId) {
    try {
      let url = posProductsUrl + '?'
      if (q) url += `q=${encodeURIComponent(q)}&`
      if (catId) url += `category=${catId}`
      const res = await fetch(url, { credentials: 'include', headers: { 'X-CSRFToken': getCookie('csrftoken') } })
      if (res.ok) setProducts(await res.json())
    } catch (e) { console.error(e) }
  }

  function handleSearch(q) { setSearchQuery(q) }
  function handleCategorySelect(catId) {
    setSelectedCategory(prev => prev === catId ? null : catId)
    setSearchQuery('')
  }

  async function addToCart(product) {
    try {
      const res = await apiPost(cartAddUrl, { product_id: product.id, quantity: 1 })
      setToast({ message: `Added "${product.name}"`, type: 'success' })
      await loadCart()
    } catch (e) { setToast({ message: 'Failed to add product', type: 'error' }) }
  }

  async function removeFromCart(itemId) {
    try {
      await fetch(`${cartRemoveBase}${itemId}/`, {
        credentials: 'include',
        headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' }
      })
      await loadCart()
    } catch (e) { setToast({ message: 'Failed to remove item', type: 'error' }) }
  }

  async function updateCartItem(itemId, quantity) {
    try {
      await apiPost(`${cartUpdateBase}${itemId}/`, { quantity: quantity.toString() })
      await loadCart()
    } catch (e) { setToast({ message: 'Failed to update quantity', type: 'error' }) }
  }

  async function completeSale() {
    if (!transactionId) { setToast({ message: 'No active transaction', type: 'error' }); return }
    if (cart.lines.length === 0) { setToast({ message: 'Cart is empty', type: 'warning' }); return }
    if (!amountTendered || parseFloat(amountTendered) < cart.total) {
      setToast({ message: 'Amount tendered must be at least the total', type: 'warning' }); return
    }
    setCompleting(true)
    try {
      const formData = new URLSearchParams()
      formData.append('payment_method', paymentMethod)
      formData.append('amount', cart.total)
      formData.append('amount_tendered', amountTendered)
      const res = await fetch(`/sales/${transactionId}/complete/`, {
        method: 'POST', credentials: 'include',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: formData, redirect: 'follow'
      })
      if (res.ok) {
        const change = (parseFloat(amountTendered) - cart.total).toFixed(2)
        setToast({ message: `Sale completed! Change: रू ${nepaliNumber(change)}`, type: 'success' })
        setCart({ lines: [], subtotal: 0, tax: 0, total: 0, count: 0 })
        setAmountTendered(''); setTransactionId(null); setShowPayment(false)
        setTimeout(() => loadCart(), 500)
      }
    } catch (e) { setToast({ message: 'Failed to complete sale', type: 'error' }) }
    setCompleting(false)
  }

  async function payWithKhalti() {
    if (!transactionId) { setToast({ message: 'No active transaction', type: 'error' }); return }
    if (cart.lines.length === 0) { setToast({ message: 'Cart is empty', type: 'warning' }); return }
    setKhaltiLoading(true)
    try {
      const data = await apiPost('/sales/pos/khalti/initiate/')
      if (data.payment_url) {
        window.location.href = data.payment_url
        return
      }
      setToast({ message: data.error || 'Failed to start Khalti payment', type: 'error' })
    } catch (e) {
      setToast({ message: 'Failed to start Khalti payment', type: 'error' })
    }
    setKhaltiLoading(false)
  }

  function getCartQty(productId) {
    const p = products.find(p => p.id === productId)
    if (!p) return 0
    const item = cart.lines.find(l => l.sku === p.sku)
    return item ? item.quantity : 0
  }

  const cartQtyMap = {}
  cart.lines.forEach(l => { cartQtyMap[l.id] = l.quantity })

  if (loading) return (
    <div style={{ padding: 24 }}>
      <div style={{ height: 56, background: '#f1f5f9', borderRadius: 12, marginBottom: 20, animation: 'pulse 1.5s ease infinite' }} />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 16 }}>
        {[1,2,3,4,5,6,7,8].map(i => (
          <div key={i} style={{ height: 220, background: '#f1f5f9', borderRadius: 14, animation: `pulse 1.5s ease ${i * 0.08}s infinite` }} />
        ))}
      </div>
    </div>
  )

  return (
    <div style={{ minHeight: 'calc(100vh - 60px)', background: '#f8fafc' }}>
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
      {showPayment && (
        <PaymentModal
          cart={cart} paymentMethod={paymentMethod} setPaymentMethod={setPaymentMethod}
          amountTendered={amountTendered} setAmountTendered={setAmountTendered}
          onComplete={completeSale} completing={completing}
          onKhaltiPay={payWithKhalti} khaltiLoading={khaltiLoading}
          onClose={() => setShowPayment(false)}
        />
      )}
      {showMobileCart && (
        <MobileCartDrawer
          cart={cart} items={cart.lines} onRemove={removeFromCart}
          onUpdate={updateCartItem} onPayment={() => setShowPayment(true)}
          onClose={() => setShowMobileCart(false)}
        />
      )}

      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 360px', gap: 0,
        minHeight: 'calc(100vh - 60px)', alignItems: 'start',
      }} className="pos-layout">

        <div style={{ padding: '20px 24px', overflowY: 'auto' }} className="pos-left">
          <div style={{ marginBottom: 16 }}>
            <SearchBar onSearch={handleSearch} query={searchQuery} setQuery={setSearchQuery} onClear={() => loadProducts('', selectedCategory)} />
          </div>

          <div style={{ marginBottom: 16 }}>
            <CategoryBar categories={categories} selected={selectedCategory} onSelect={handleCategorySelect} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 14 }} className="pos-product-grid">
            {products.length === 0 ? (
              <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: 60, color: '#94a3b8' }}>
                <i className="fa-solid fa-box-open" style={{ fontSize: 48, marginBottom: 16, display: 'block', opacity: 0.3 }}></i>
                <p style={{ fontSize: 15, fontWeight: 600 }}>No products found</p>
                <p style={{ fontSize: 13 }}>Try a different search or category</p>
              </div>
            ) : products.map(p => (
              <ProductCard key={p.id} product={p} onAdd={addToCart} cartQty={getCartQty(p.id)} />
            ))}
          </div>
        </div>

        <div className="pos-right" style={{
          background: '#fff', borderLeft: '1px solid #e2e8f0',
          display: 'flex', flexDirection: 'column',
          maxHeight: 'calc(89vh - 60px)',
          position: 'sticky', top: 55,
          borderRadius: 0,
          margin: 0,
          boxShadow: 'none',
          transition: 'border-radius 0.3s, margin 0.3s, box-shadow 0.3s',
        }}>
          <div style={{
            padding: '16px 20px', borderBottom: '1px solid #f1f5f9',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <i className="fa-solid fa-cart-shopping" style={{ color: '#3b82f6', fontSize: 18 }}></i>
              <span style={{ fontWeight: 700, fontSize: 16, color: '#1e293b' }}>Current Order</span>
            </div>
            {cart.count > 0 && (
              <span style={{
                background: '#3b82f6', color: '#fff', borderRadius: 20, padding: '3px 12px',
                fontSize: 12, fontWeight: 700,
              }}>{cart.count}</span>
            )}
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', minHeight: 0 }}>
            {cart.lines.length === 0 ? (
              <div style={{
                textAlign: 'center', padding: '28px 16px', color: '#94a3b8',
                display: 'flex', flexDirection: 'column', alignItems: 'center',
              }}>
                <div style={{
                  width: 48, height: 48, borderRadius: 12, background: '#f1f5f9',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 10,
                }}>
                  <i className="fa-solid fa-cart-shopping" style={{ fontSize: 20, opacity: 0.3 }}></i>
                </div>
                <p style={{ fontSize: 13, fontWeight: 600, marginBottom: 2 }}>Cart is empty</p>
                <p style={{ fontSize: 11, lineHeight: 1.5 }}>Click products to add items</p>
              </div>
            ) : cart.lines.map(item => (
              <CartItem key={item.id} item={item} onRemove={removeFromCart} onUpdate={updateCartItem} />
            ))}
          </div>

          {cart.lines.length > 0 && (
            <div style={{ padding: '16px 20px', borderTop: '1px solid #f1f5f9', background: '#f8fafc' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
                <span style={{ color: '#64748b' }}>Subtotal</span>
                <span style={{ fontWeight: 600, color: '#1e293b' }}>रू {nepaliNumber(cart.subtotal)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10, fontSize: 13 }}>
                <span style={{ color: '#64748b' }}>Tax</span>
                <span style={{ fontWeight: 600, color: '#1e293b' }}>रू {nepaliNumber(cart.tax)}</span>
              </div>
              <div style={{
                display: 'flex', justifyContent: 'space-between', marginBottom: 16,
                paddingBottom: 14, borderBottom: '2px solid #e2e8f0',
              }}>
                <span style={{ fontWeight: 800, fontSize: 15, color: '#1e293b' }}>Total</span>
                <span style={{ fontWeight: 900, fontSize: 24, color: '#3b82f6' }}>रू {nepaliNumber(cart.total)}</span>
              </div>
              <button
                onClick={() => setShowPayment(true)}
                style={{
                  width: '100%', padding: '15px', border: 'none', borderRadius: 12,
                  background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                  color: '#fff', fontSize: 15, fontWeight: 700, cursor: 'pointer',
                  boxShadow: '0 6px 20px rgba(59,130,246,0.35)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
                  transition: 'all 0.2s',
                }}
                onMouseEnter={e => e.currentTarget.style.boxShadow = '0 8px 30px rgba(59,130,246,0.45)'}
                onMouseLeave={e => e.currentTarget.style.boxShadow = '0 6px 20px rgba(59,130,246,0.35)'}
              >
                <i className="fa-solid fa-credit-card"></i> Proceed to Payment
              </button>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={() => setShowMobileCart(true)}
        className="pos-mobile-cart-btn"
        style={{
          display: 'none', position: 'fixed', bottom: 20, right: 20, zIndex: 7000,
          width: 60, height: 60, borderRadius: 16, border: 'none',
          background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
          color: '#fff', fontSize: 24, cursor: 'pointer',
          boxShadow: '0 8px 30px rgba(59,130,246,0.4)',
          alignItems: 'center', justifyContent: 'center',
        }}
      >
        <i className="fa-solid fa-cart-shopping"></i>
        {cart.count > 0 && (
          <span style={{
            position: 'absolute', top: -4, right: -4,
            background: '#ef4444', color: '#fff', borderRadius: 10,
            width: 22, height: 22, fontSize: 11, fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>{cart.count}</span>
        )}
      </button>
    </div>
  )
}
