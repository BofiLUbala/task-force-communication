import { SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useAuth } from '../context/AuthContext';
import { colors } from '../theme/colors';

export default function HomeScreen() {
  const { user, logout } = useAuth();

  return (
    <SafeAreaView style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.title}>Bienvenue, {user?.full_name}</Text>
        <Text style={styles.subtitle}>Rôle : {user?.role === 'HIERARCHY' ? 'Hiérarchie' : 'Agent terrain'}</Text>
      </View>

      <View style={styles.placeholder}>
        <Text style={styles.placeholderText}>
          Écran suivant : liste des rapports et dépôt de contenu terrain (photo/vidéo/document),
          avec sauvegarde hors-ligne et synchronisation automatique.
        </Text>
      </View>

      <TouchableOpacity style={styles.logoutButton} onPress={logout}>
        <Text style={styles.logoutText}>Déconnexion</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.gray, padding: 20 },
  header: { marginBottom: 24 },
  title: { fontSize: 20, fontWeight: '700', color: colors.navy },
  subtitle: { fontSize: 13, color: '#5c6470', marginTop: 4 },
  placeholder: { backgroundColor: colors.white, borderRadius: 10, padding: 18 },
  placeholderText: { color: '#5c6470', fontSize: 13, lineHeight: 20 },
  logoutButton: { marginTop: 'auto', alignItems: 'center', paddingVertical: 14 },
  logoutText: { color: colors.rejected, fontWeight: '600' },
});
