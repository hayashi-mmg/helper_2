import { useRef } from 'react'
import {
  DialogRoot,
  DialogContent,
  DialogHeader,
  DialogBody,
  DialogFooter,
  DialogTitle,
  DialogCloseTrigger,
  DialogBackdrop,
  DialogPositioner,
  Button,
  Text,
} from '@chakra-ui/react'

interface ConfirmDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  colorPalette?: string
  loading?: boolean
}

export default function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = '削除',
  cancelLabel = 'キャンセル',
  colorPalette = 'red',
  loading = false,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null)

  return (
    <DialogRoot open={open} onOpenChange={(e) => !e.open && onClose()} initialFocusEl={() => cancelRef.current}>
      <DialogBackdrop />
      <DialogPositioner>
        <DialogContent borderRadius="xl" p={2}>
          <DialogHeader>
            <DialogTitle fontSize="xl" color="text.primary">{title}</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text fontSize="lg" color="text.secondary">{message}</Text>
          </DialogBody>
          <DialogFooter gap={3}>
            <Button
              ref={cancelRef}
              variant="outline"
              size="lg"
              onClick={onClose}
            >
              {cancelLabel}
            </Button>
            <Button
              colorPalette={colorPalette}
              size="lg"
              onClick={onConfirm}
              loading={loading}
            >
              {confirmLabel}
            </Button>
          </DialogFooter>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogPositioner>
    </DialogRoot>
  )
}
