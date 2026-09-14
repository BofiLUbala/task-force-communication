import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Image,
  RefreshControl,
  SafeAreaView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { useAuth } from '../context/AuthContext';
import { colors } from '../theme/colors';
import {
  TYPE_LABELS,
  coverOf,
  fetchFeed,
  previewText,
  relativeTime,
} from '../api/publications';

/**
 * The agent's home screen: the publications that concern them.
 *
 * The list is whatever `/publications/feed/` returns. This screen never
 * decides what an agent may see — the server has already applied the
 * publication's audience before the rows reach the device.
 */
export default function HomeScreen({ navigation }) {
  const { user, logout } = useAuth();
  const [posts, setPosts] = useState([]);
  const [unread, setUnread] = useState(0);
  const [state, setState] = useState('loading');
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async ({ silent } = {}) => {
    if (!silent) setState('loading');
    try {
      const { posts: rows, unreadCount } = await fetchFeed();
      setPosts(rows);
      setUnread(unreadCount);
      setState('ready');
    } catch {
      setState('error');
    }
  }, []);

  useEffect(() => {
    load();
    // Coming back from a publication should reflect that it was just read.
    const unsubscribe = navigation?.addListener?.('focus', () => load({ silent: true }));
    return unsubscribe;
  }, [load, navigation]);

  async function refresh() {
    setRefreshing(true);
    await load({ silent: true });
    setRefreshing(false);
  }

  function open(post) {
    navigation.navigate('PublicationDetail', { slug: post.slug, title: post.title });
  }

  function renderCard({ item }) {
    const cover = coverOf(item);
    const text = previewText(item);
    return (
      <TouchableOpacity
        style={[styles.card, !item.is_read && styles.cardUnread]}
        onPress={() => open(item)}
        activeOpacity={0.85}
      >
        <View style={styles.cardHead}>
          <Text style={styles.badge}>
            {(TYPE_LABELS[item.category] || item.category).toUpperCase()}
          </Text>
          <Text style={styles.cardTime}>{relativeTime(item.published_at || item.created_at)}</Text>
        </View>
        <Text style={styles.cardTitle}>{item.title}</Text>
        {cover ? <Image source={{ uri: cover }} style={styles.cardImage} resizeMode="cover" /> : null}
        {text ? (
          <Text style={styles.cardPreview} numberOfLines={3}>{text}</Text>
        ) : null}
        <Text style={styles.cardMore}>Voir plus ›</Text>
      </TouchableOpacity>
    );
  }

  const header = (
    <View style={styles.header}>
      <Text style={styles.greeting}>Bonjour {user?.full_name}</Text>
      <Text style={styles.subtitle}>
        {unread > 0
          ? `${unread} nouvelle${unread > 1 ? 's' : ''} publication${unread > 1 ? 's' : ''}`
          : 'Aucune nouvelle publication'}
      </Text>
    </View>
  );

  if (state === 'loading') {
    return (
      <SafeAreaView style={[styles.screen, styles.centered]}>
        <ActivityIndicator color={colors.navy} size="large" />
        <Text style={styles.stateText}>Chargement des publications...</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.screen}>
      <FlatList
        data={posts}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderCard}
        ListHeaderComponent={header}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} />}
        ListEmptyComponent={(
          <View style={styles.empty}>
            <Text style={styles.stateText}>
              {state === 'error'
                ? 'Impossible de charger les publications. Tirez pour réessayer.'
                : 'Aucune publication ne vous concerne pour le moment.'}
            </Text>
          </View>
        )}
      />

      <TouchableOpacity style={styles.logoutButton} onPress={logout}>
        <Text style={styles.logoutText}>Déconnexion</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.gray },
  centered: { alignItems: 'center', justifyContent: 'center' },
  list: { padding: 20, paddingBottom: 8 },
  header: { marginBottom: 18 },
  greeting: { fontSize: 20, fontWeight: '700', color: colors.navy },
  subtitle: { fontSize: 13, color: '#5c6470', marginTop: 4 },

  card: {
    backgroundColor: colors.white, borderRadius: 12, padding: 16, marginBottom: 12,
    borderLeftWidth: 3, borderLeftColor: 'transparent',
  },
  cardUnread: { borderLeftColor: colors.gold },
  cardHead: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  badge: {
    fontSize: 10, fontWeight: '700', letterSpacing: 0.6, color: colors.navy,
    backgroundColor: '#e6eeff', paddingHorizontal: 9, paddingVertical: 4, borderRadius: 999,
    overflow: 'hidden',
  },
  cardTime: { fontSize: 11, color: '#8a909b' },
  cardTitle: { fontSize: 15, fontWeight: '700', color: colors.navy, lineHeight: 21 },
  cardImage: { width: '100%', height: 150, borderRadius: 9, marginTop: 10 },
  cardPreview: { fontSize: 13, color: '#5c6470', lineHeight: 19, marginTop: 9 },
  cardMore: { marginTop: 11, fontSize: 13, fontWeight: '700', color: colors.navyLight },

  empty: { paddingVertical: 40, alignItems: 'center' },
  stateText: { color: '#5c6470', fontSize: 13, textAlign: 'center', marginTop: 10 },
  logoutButton: { alignItems: 'center', paddingVertical: 14 },
  logoutText: { color: colors.rejected, fontWeight: '600' },
});
