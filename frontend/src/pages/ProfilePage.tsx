import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box, Button, Text, VStack, HStack, Badge, Input, Textarea,
} from '@chakra-ui/react'
import { changePassword, getProfile, updateProfile } from '@/api/users'
import PageHeader from '@/components/ui/PageHeader'
import FormField from '@/components/ui/FormField'
import LoadingState from '@/components/ui/LoadingState'
import { toaster } from '@/components/ui/toaster'
import ThemeSelector from '@/components/theme/ThemeSelector'

const ROLE_LABELS: Record<string, string> = {
  senior: '利用者',
  helper: 'ヘルパー',
  care_manager: 'ケアマネージャー',
}

const ROLE_COLORS: Record<string, string> = {
  senior: 'green',
  helper: 'blue',
  care_manager: 'purple',
}

function ProfileField({ label, value }: { label: string; value: string | undefined }) {
  return (
    <Box py={3} borderBottom="1px solid" borderColor="border.default" _last={{ border: 'none' }}>
      <Text fontSize="sm" color="text.muted" mb={1}>{label}</Text>
      <Text fontSize="md" color={value ? 'text.primary' : 'text.muted'} fontWeight={value ? 'medium' : 'normal'}>
        {value || '未設定'}
      </Text>
    </Box>
  )
}

interface ApiError {
  response?: { data?: { detail?: string } }
}

export default function ProfilePage() {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [showPasswordForm, setShowPasswordForm] = useState(false)
  const [pwForm, setPwForm] = useState({ current: '', newPw: '', confirm: '' })
  const [pwError, setPwError] = useState('')
  const [form, setForm] = useState({
    full_name: '',
    phone: '',
    address: '',
    emergency_contact: '',
    medical_notes: '',
  })

  const { data: user, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
  })

  useEffect(() => {
    if (user) {
      setForm({
        full_name: user.full_name || '',
        phone: user.phone || '',
        address: user.address || '',
        emergency_contact: user.emergency_contact || '',
        medical_notes: user.medical_notes || '',
      })
    }
  }, [user])

  const passwordMutation = useMutation({
    mutationFn: () => changePassword(pwForm.current, pwForm.newPw),
    onSuccess: () => {
      setShowPasswordForm(false)
      setPwForm({ current: '', newPw: '', confirm: '' })
      setPwError('')
      toaster.success({ title: 'パスワードを変更しました' })
    },
    onError: (err: ApiError) => {
      setPwError(err.response?.data?.detail ?? 'エラーが発生しました')
    },
  })

  const handlePasswordSubmit = () => {
    setPwError('')
    if (pwForm.newPw.length < 8) {
      setPwError('新しいパスワードは8文字以上で入力してください')
      return
    }
    if (pwForm.newPw !== pwForm.confirm) {
      setPwError('新しいパスワードが一致しません')
      return
    }
    passwordMutation.mutate()
  }

  const updateMutation = useMutation({
    mutationFn: () => updateProfile({
      full_name: form.full_name || undefined,
      phone: form.phone || undefined,
      address: form.address || undefined,
      emergency_contact: form.emergency_contact || undefined,
      medical_notes: form.medical_notes || undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      setEditing(false)
      toaster.success({ title: 'プロファイルを更新しました' })
    },
  })

  if (isLoading) return <LoadingState type="form" count={5} />
  if (!user) return (
    <Box p={8} bg="bg.card" borderRadius="xl" textAlign="center">
      <Text color="text.muted">プロファイルが見つかりません</Text>
    </Box>
  )

  return (
    <Box>
      <PageHeader title="プロファイル">
        {!editing && (
          <Button
            bg="brand.600"
            color="white"
            _hover={{ bg: 'brand.700' }}
            size="lg"
            onClick={() => setEditing(true)}
          >
            編集
          </Button>
        )}
      </PageHeader>

      <Box
        bg="bg.card"
        borderRadius="xl"
        border="1px solid"
        borderColor="border.default"
        maxW="640px"
        overflow="hidden"
      >
        {/* Profile Header */}
        <Box bg="brand.50" px={8} py={6} borderBottom="1px solid" borderColor="border.default">
          <HStack gap={4}>
            <Box
              w="56px"
              h="56px"
              bg="brand.600"
              borderRadius="full"
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </Box>
            <VStack align="start" gap={1}>
              <Text fontSize="xl" fontWeight="bold" color="text.primary">{user.full_name}</Text>
              <HStack gap={2}>
                <Badge
                  colorPalette={ROLE_COLORS[user.role] || 'gray'}
                  variant="subtle"
                  fontSize="sm"
                  px={3}
                  py={1}
                >
                  {ROLE_LABELS[user.role] || user.role}
                </Badge>
                <Text fontSize="sm" color="text.muted">{user.email}</Text>
              </HStack>
            </VStack>
          </HStack>
        </Box>

        {/* Profile Body */}
        <Box px={8} py={4}>
          {editing ? (
            <form onSubmit={(e) => { e.preventDefault(); updateMutation.mutate() }}>
              <VStack gap={4} align="stretch" py={2}>
                <FormField label="氏名">
                  <Input
                    value={form.full_name}
                    onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                    size="lg"
                    borderRadius="lg"
                  />
                </FormField>
                <FormField label="電話番号">
                  <Input
                    value={form.phone}
                    onChange={(e) => setForm({ ...form, phone: e.target.value })}
                    size="lg"
                    borderRadius="lg"
                  />
                </FormField>
                <FormField label="住所">
                  <Input
                    value={form.address}
                    onChange={(e) => setForm({ ...form, address: e.target.value })}
                    size="lg"
                    borderRadius="lg"
                  />
                </FormField>
                <FormField label="緊急連絡先">
                  <Input
                    value={form.emergency_contact}
                    onChange={(e) => setForm({ ...form, emergency_contact: e.target.value })}
                    size="lg"
                    borderRadius="lg"
                  />
                </FormField>
                <FormField label="医療メモ">
                  <Textarea
                    value={form.medical_notes}
                    onChange={(e) => setForm({ ...form, medical_notes: e.target.value })}
                    borderRadius="lg"
                    rows={3}
                  />
                </FormField>
                <HStack gap={3} pt={2}>
                  <Button
                    type="submit"
                    bg="brand.600"
                    color="white"
                    _hover={{ bg: 'brand.700' }}
                    size="lg"
                    loading={updateMutation.isPending}
                  >
                    保存
                  </Button>
                  <Button size="lg" variant="outline" onClick={() => setEditing(false)}>
                    キャンセル
                  </Button>
                </HStack>
              </VStack>
            </form>
          ) : (
            <>
              <ProfileField label="氏名" value={user.full_name} />
              <ProfileField label="電話番号" value={user.phone} />
              <ProfileField label="住所" value={user.address} />
              <ProfileField label="緊急連絡先" value={user.emergency_contact} />
              <ProfileField label="医療メモ" value={user.medical_notes} />
              {user.care_level != null && (
                <ProfileField label="介護度" value={String(user.care_level)} />
              )}
              <ProfileField label="登録日" value={new Date(user.created_at).toLocaleDateString('ja-JP')} />
            </>
          )}
        </Box>
      </Box>

      {/* パスワード変更セクション */}
      <Box mt={6} maxW="640px">
        {!showPasswordForm ? (
          <Button variant="outline" onClick={() => setShowPasswordForm(true)}>
            パスワード変更
          </Button>
        ) : (
          <Box
            bg="bg.card"
            borderRadius="xl"
            border="1px solid"
            borderColor="border.default"
            p={8}
          >
            <VStack align="stretch" gap={4}>
              <Text fontSize="lg" fontWeight="bold">パスワード変更</Text>
              {pwError && (
                <Box bg="red.50" color="red.600" p={3} borderRadius="md" fontSize="sm">
                  {pwError}
                </Box>
              )}
              <FormField label="現在のパスワード" required>
                <Input
                  type="password"
                  value={pwForm.current}
                  onChange={(e) => setPwForm({ ...pwForm, current: e.target.value })}
                  size="lg"
                  borderRadius="lg"
                />
              </FormField>
              <FormField label="新しいパスワード" required>
                <Input
                  type="password"
                  value={pwForm.newPw}
                  onChange={(e) => setPwForm({ ...pwForm, newPw: e.target.value })}
                  size="lg"
                  borderRadius="lg"
                />
              </FormField>
              <FormField label="新しいパスワード（確認）" required>
                <Input
                  type="password"
                  value={pwForm.confirm}
                  onChange={(e) => setPwForm({ ...pwForm, confirm: e.target.value })}
                  size="lg"
                  borderRadius="lg"
                />
              </FormField>
              <HStack gap={3} pt={2}>
                <Button
                  bg="brand.600"
                  color="white"
                  _hover={{ bg: 'brand.700' }}
                  size="lg"
                  onClick={handlePasswordSubmit}
                  loading={passwordMutation.isPending}
                  disabled={!pwForm.current || !pwForm.newPw || !pwForm.confirm}
                >
                  変更する
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  onClick={() => { setShowPasswordForm(false); setPwForm({ current: '', newPw: '', confirm: '' }); setPwError('') }}
                >
                  キャンセル
                </Button>
              </HStack>
            </VStack>
          </Box>
        )}
      </Box>

      {/* テーマ選択セクション */}
      <Box mt={8} maxW="640px">
        <Box
          bg="bg.card"
          borderRadius="xl"
          border="1px solid"
          borderColor="border.default"
          px={8}
          py={6}
        >
          <Text
            id="theme-heading"
            as="h2"
            fontSize="xl"
            fontWeight="bold"
            color="text.primary"
            mb={4}
          >
            表示テーマ
          </Text>
          <Text fontSize="sm" color="text.secondary" mb={4}>
            画面の配色・書体を選択できます。変更は即座に全画面へ反映されます。
          </Text>
          <ThemeSelector />
        </Box>
      </Box>
    </Box>
  )
}
