import { toast } from 'sonner'
export const notify = { success: (m) => toast.success(m), error: (m) => toast.error(m), info: (m) => toast.info(m), warning: (m) => toast.warning(m), loading: (m) => toast.loading(m) }
