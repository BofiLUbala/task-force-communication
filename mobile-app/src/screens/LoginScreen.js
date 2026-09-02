import { useState } from 'react';
import {
  ActivityIndicator,
  Image,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { colors } from '../theme/colors';

export default function LoginScreen() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleLogin() {
    if (!username || !password) {
      setError('Veuillez remplir tous les champs.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await login(username, password);
    } catch {
      setError('Identifiants incorrects. Veuillez réessayer.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.card}>
        <View style={styles.emblem}>
          <Image
            source={require('../../assets/logo-taskforce.jpg')}
            style={styles.emblemImage}
            accessibilityLabel="Logo officiel de la Task Force Présidentielle"
          />
        </View>
        <Text style={styles.title}>Espace agents terrain</Text>
        <Text style={styles.subtitle}>Task Force Présidentielle — RDC</Text>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        <Text style={styles.label}>Identifiant</Text>
        <TextInput
          style={styles.input}
          value={username}
          onChangeText={setUsername}
          placeholder="matricule ou identifiant"
          placeholderTextColor="rgba(255,255,255,0.4)"
          autoCapitalize="none"
        />

        <Text style={styles.label}>Mot de passe</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          placeholder="••••••••"
          placeholderTextColor="rgba(255,255,255,0.4)"
          secureTextEntry
        />

        <TouchableOpacity style={styles.button} onPress={handleLogin} disabled={loading}>
          {loading ? (
            <ActivityIndicator color={colors.navy} />
          ) : (
            <Text style={styles.buttonText}>Se connecter</Text>
          )}
        </TouchableOpacity>

        <Text style={styles.notice}>
          Accès strictement réservé au personnel autorisé de la Task Force Présidentielle.
        </Text>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
    backgroundColor: colors.navy,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    width: '100%',
    maxWidth: 380,
    backgroundColor: 'rgba(255,255,255,0.06)',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.12)',
    padding: 28,
  },
  emblem: {
    width: 112,
    height: 112,
    borderRadius: 56,
    alignSelf: 'center',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 20,
  },
  emblemImage: {
    position: 'absolute',
    width: '328%',
    height: '152%',
    left: '-8.5%',
    top: '-32.5%',
  },
  title: { color: colors.white, fontSize: 18, fontWeight: '700', textAlign: 'center' },
  subtitle: { color: colors.textMuted, fontSize: 13, textAlign: 'center', marginTop: 4, marginBottom: 24 },
  label: { color: 'rgba(255,255,255,0.75)', fontSize: 13, marginBottom: 6, marginTop: 12 },
  input: {
    backgroundColor: 'rgba(255,255,255,0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.2)',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: colors.white,
    fontSize: 15,
  },
  button: {
    backgroundColor: colors.gold,
    borderRadius: 8,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 24,
  },
  buttonText: { color: colors.navy, fontWeight: '700', fontSize: 15 },
  error: {
    color: '#ffb3b3',
    backgroundColor: 'rgba(197,48,48,0.2)',
    borderWidth: 1,
    borderColor: colors.rejected,
    borderRadius: 8,
    padding: 10,
    fontSize: 13,
    marginBottom: 8,
  },
  notice: { color: 'rgba(255,255,255,0.45)', fontSize: 11, textAlign: 'center', marginTop: 20, lineHeight: 16 },
});
