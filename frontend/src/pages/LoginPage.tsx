import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Button, Heading, Input, Text, VStack, HStack } from '@chakra-ui/react'
import { login, validateQR } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import FormField from '@/components/ui/FormField'

type LoginMode = 'password' | 'qr'

export default function LoginPage() {
  const [mode, setMode] = useState<LoginMode>('password')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [qrToken, setQrToken] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((state) => state.setAuth)
  const navigate = useNavigate()

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = await login(email, password)
      setAuth(data.access_token, data.refresh_token, data.user)
      navigate('/')
    } catch {
      setError('メールアドレスまたはパスワードが正しくありません')
    } finally {
      setLoading(false)
    }
  }

  const handleQRLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const data = await validateQR(qrToken)
      setAuth(data.access_token, data.refresh_token, data.user)
      navigate('/')
    } catch {
      setError('QRコードが無効または期限切れです')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box minH="100vh" display="flex" alignItems="center" justifyContent="center" bg="bg.page">
      <Box w="full" maxW="480px" px={4}>
        {/* Logo & Title */}
        <VStack gap={3} mb={8} textAlign="center">
          <Box
            w="64px"
            h="64px"
            bg="brand.600"
            borderRadius="2xl"
            display="flex"
            alignItems="center"
            justifyContent="center"
          >
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
          </Box>
          <Heading size="xl" color="text.primary" fontWeight="bold">
            ホームヘルパー管理システム
          </Heading>
          <Text fontSize="md" color="text.muted">
            ログインしてください
          </Text>
        </VStack>

        {/* Login Card */}
        <Box
          bg="bg.card"
          p={8}
          borderRadius="2xl"
          shadow="lg"
          border="1px solid"
          borderColor="border.default"
        >
          <VStack gap={6}>
            {/* Mode Tabs */}
            <HStack gap={2} w="full" bg="bg.muted" p={1} borderRadius="xl">
              <Button
                flex={1}
                size="lg"
                borderRadius="lg"
                bg={mode === 'password' ? 'bg.card' : 'transparent'}
                color={mode === 'password' ? 'brand.600' : 'text.muted'}
                shadow={mode === 'password' ? 'sm' : 'none'}
                fontWeight={mode === 'password' ? 'bold' : 'medium'}
                _hover={{ color: 'brand.600' }}
                onClick={() => { setMode('password'); setError('') }}
              >
                パスワード
              </Button>
              <Button
                flex={1}
                size="lg"
                borderRadius="lg"
                bg={mode === 'qr' ? 'bg.card' : 'transparent'}
                color={mode === 'qr' ? 'brand.600' : 'text.muted'}
                shadow={mode === 'qr' ? 'sm' : 'none'}
                fontWeight={mode === 'qr' ? 'bold' : 'medium'}
                _hover={{ color: 'brand.600' }}
                onClick={() => { setMode('qr'); setError('') }}
              >
                QRコード
              </Button>
            </HStack>

            {mode === 'password' ? (
              <form onSubmit={handlePasswordLogin} style={{ width: '100%' }}>
                <VStack gap={5} w="full">
                  <FormField label="メールアドレス" required>
                    <Input
                      type="email"
                      placeholder="example@email.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      size="lg"
                      borderRadius="lg"
                      required
                    />
                  </FormField>
                  <FormField label="パスワード" required>
                    <Input
                      type="password"
                      placeholder="パスワードを入力"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      size="lg"
                      borderRadius="lg"
                      required
                    />
                  </FormField>
                  {error && (
                    <Box w="full" bg="danger.50" border="1px solid" borderColor="danger.100" borderRadius="lg" px={4} py={3}>
                      <Text color="danger.600" fontSize="md">{error}</Text>
                    </Box>
                  )}
                  <Button
                    type="submit"
                    bg="brand.600"
                    color="white"
                    _hover={{ bg: 'brand.700' }}
                    size="lg"
                    w="full"
                    borderRadius="lg"
                    loading={loading}
                  >
                    ログイン
                  </Button>
                </VStack>
              </form>
            ) : (
              <form onSubmit={handleQRLogin} style={{ width: '100%' }}>
                <VStack gap={5} w="full">
                  <Text fontSize="md" color="text.secondary" textAlign="center" lineHeight="tall">
                    ケアマネージャーから受け取った
                    <br />
                    QRコードのトークンを入力してください
                  </Text>
                  <FormField label="QRトークン" required>
                    <Input
                      placeholder="トークンを入力"
                      value={qrToken}
                      onChange={(e) => setQrToken(e.target.value)}
                      size="lg"
                      borderRadius="lg"
                      required
                    />
                  </FormField>
                  {error && (
                    <Box w="full" bg="danger.50" border="1px solid" borderColor="danger.100" borderRadius="lg" px={4} py={3}>
                      <Text color="danger.600" fontSize="md">{error}</Text>
                    </Box>
                  )}
                  <Button
                    type="submit"
                    bg="brand.600"
                    color="white"
                    _hover={{ bg: 'brand.700' }}
                    size="lg"
                    w="full"
                    borderRadius="lg"
                    loading={loading}
                  >
                    QRコードでログイン
                  </Button>
                </VStack>
              </form>
            )}
          </VStack>
        </Box>
      </Box>
    </Box>
  )
}
