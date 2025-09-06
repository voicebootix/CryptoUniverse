import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(amount: number, currency: string = 'USD', locale?: string): string {
  try {
    // Determine appropriate locale
    const resolvedLocale = locale || (typeof navigator !== 'undefined' ? navigator.language : 'en-US');
    
    // Create formatter to determine currency-native fraction digits
    const formatter = new Intl.NumberFormat(resolvedLocale, {
      style: 'currency',
      currency,
    });
    
    const options = formatter.resolvedOptions();
    const fractionDigits = options.maximumFractionDigits || 2;
    
    // Format with proper fraction digits for the currency
    return new Intl.NumberFormat(resolvedLocale, {
      style: 'currency',
      currency,
      minimumFractionDigits: fractionDigits,
      maximumFractionDigits: fractionDigits,
    }).format(amount);
  } catch (error) {
    // Fallback: construct string manually using resolved fraction digits
    try {
      const resolvedLocale = locale || 'en-US';
      const testFormatter = new Intl.NumberFormat(resolvedLocale, {
        style: 'currency',
        currency,
      });
      const fractionDigits = testFormatter.resolvedOptions().maximumFractionDigits || 2;
      
      return amount.toFixed(fractionDigits) + ' ' + currency;
    } catch (fallbackError) {
      // Final fallback
      return amount.toFixed(2) + ' ' + currency;
    }
  }
}

export function formatNumber(value: number, decimals: number = 2): string {
  try {
    // Validate and normalize decimals
    const normalizedDecimals = Math.max(0, Math.min(20, Math.trunc(decimals || 0)));
    
    // Use navigator language when available
    const locale = (typeof navigator !== 'undefined' ? navigator.language : undefined) || 'en-US';
    
    return new Intl.NumberFormat(locale, {
      minimumFractionDigits: normalizedDecimals,
      maximumFractionDigits: normalizedDecimals,
    }).format(value);
  } catch (error) {
    // Fallback with sanitized decimals
    const normalizedDecimals = Math.max(0, Math.min(20, Math.trunc(decimals || 0)));
    return value.toFixed(normalizedDecimals);
  }
}

export function formatPercentage(value: number, decimals: number = 2): string {
  try {
    // Validate and normalize decimals
    const normalizedDecimals = Math.max(0, Math.min(20, Math.trunc(decimals || 0)));
    
    // Use navigator language when available  
    const locale = (typeof navigator !== 'undefined' ? navigator.language : undefined) || 'en-US';
    
    return new Intl.NumberFormat(locale, {
      style: 'percent',
      minimumFractionDigits: normalizedDecimals,
      maximumFractionDigits: normalizedDecimals,
    }).format(value / 100);
  } catch (error) {
    // Localized fallback with sanitized decimals
    const normalizedDecimals = Math.max(0, Math.min(20, Math.trunc(decimals || 0)));
    const locale = (typeof navigator !== 'undefined' ? navigator.language : undefined) || 'en-US';
    
    try {
      return (value / 100).toLocaleString(locale, {
        style: 'percent',
        minimumFractionDigits: normalizedDecimals,
        maximumFractionDigits: normalizedDecimals,
      });
    } catch (fallbackError) {
      // Final fallback
      return (value / 100).toFixed(normalizedDecimals) + '%';
    }
  }
}

export function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

export function formatRelativeTime(date: Date): string {
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
  const now = new Date()
  const diffInSeconds = Math.floor((date.getTime() - now.getTime()) / 1000)
  
  if (Math.abs(diffInSeconds) < 60) {
    return rtf.format(diffInSeconds, 'second')
  }
  
  const diffInMinutes = Math.floor(diffInSeconds / 60)
  if (Math.abs(diffInMinutes) < 60) {
    return rtf.format(diffInMinutes, 'minute')
  }
  
  const diffInHours = Math.floor(diffInMinutes / 60)
  if (Math.abs(diffInHours) < 24) {
    return rtf.format(diffInHours, 'hour')
  }
  
  const diffInDays = Math.floor(diffInHours / 24)
  return rtf.format(diffInDays, 'day')
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map(part => part.charAt(0).toUpperCase())
    .join('')
    .slice(0, 2)
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

export function generateId(length: number = 8): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let result = ''
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}

export function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard) {
    return navigator.clipboard.writeText(text)
  }
  
  // Fallback for older browsers
  const textArea = document.createElement('textarea')
  textArea.value = text
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  
  try {
    document.execCommand('copy')
    return Promise.resolve()
  } catch (err) {
    return Promise.reject(err)
  } finally {
    document.body.removeChild(textArea)
  }
}

export function downloadFile(content: string, filename: string, type: string = 'text/plain'): void {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export function isValidUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

export function truncateString(str: string, length: number): string {
  if (str.length <= length) return str
  return str.slice(0, length) + '...'
}

export function capitalizeFirst(str: string): string {
  if (!str) return str
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase()
}

export function toTitleCase(str: string): string {
  return str.replace(/\w\S*/g, (txt) =>
    txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase()
  )
}

export function parseJwt(token: string): any {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch (error) {
    return null
  }
}

export function isTokenExpired(token: string): boolean {
  const decoded = parseJwt(token)
  if (!decoded || !decoded.exp) return true
  
  const currentTime = Date.now() / 1000
  return decoded.exp < currentTime
}

export function getColorForChange(change: number): string {
  if (change > 0) return 'text-profit'
  if (change < 0) return 'text-loss'
  return 'text-muted-foreground'
}

export function getBackgroundColorForChange(change: number): string {
  if (change > 0) return 'bg-profit/10 border-profit/30'
  if (change < 0) return 'bg-loss/10 border-loss/30'
  return 'bg-muted/10 border-muted/30'
}
