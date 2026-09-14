import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  Linking,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { colors } from '../theme/colors';
import {
  TYPE_LABELS,
  fetchPublication,
  markRead,
  previewText,
  relativeTime,
  splitAttachments,
} from '../api/publications';

function Resource({ icon, label, url }) {
  return (
    <TouchableOpacity style={styles.resource} onPress={() => Linking.openURL(url)}>
      <Text style={styles.resourceIcon}>{icon}</Text>
      <Text style={styles.resourceLabel} numberOfLines={2}>{label}</Text>
      <Text style={styles.resourceOpen}>Ouvrir</Text>
    </TouchableOpacity>
  );
}

/**
 * One publication, rendered for a phone.
 *
 * Rich text is flattened rather than rendered as HTML: pulling a WebView in
 * to display body markup would mean shipping arbitrary stored HTML into a
 * privileged context, and the flattened text carries the content faithfully.
 * Videos and documents open in the system viewer through their own links.
 */
export default function PublicationDetailScreen({ route, navigation }) {
  const { slug } = route.params;
  const [post, setPost] = useState(null);
  const [state, setState] = useState('loading');

  useEffect(() => {
    let cancelled = false;
    fetchPublication(slug)
      .then((data) => {
        if (cancelled) return;
        setPost(data);
        setState('ready');
        navigation.setOptions?.({ title: data.title });
        markRead(slug);
      })
      .catch(() => !cancelled && setState('error'));
    return () => { cancelled = true; };
  }, [slug, navigation]);

  if (state === 'loading') {
    return (
      <SafeAreaView style={[styles.screen, styles.centered]}>
        <ActivityIndicator color={colors.navy} size="large" />
      </SafeAreaView>
    );
  }

  if (state === 'error') {
    return (
      <SafeAreaView style={[styles.screen, styles.centered]}>
        <Text style={styles.stateText}>
          Cette publication est introuvable ou ne vous est pas destinée.
        </Text>
        <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
          <Text style={styles.backText}>Retour</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  const { photos, videos, documents } = splitAttachments(post);
  const links = post.links || [];

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.metaRow}>
          <Text style={styles.badge}>
            {(TYPE_LABELS[post.category] || post.category).toUpperCase()}
          </Text>
          <Text style={styles.metaTime}>{relativeTime(post.published_at || post.created_at)}</Text>
        </View>

        <Text style={styles.title}>{post.title}</Text>
        {post.published_by_name ? (
          <Text style={styles.author}>Publié par {post.published_by_name}</Text>
        ) : null}

        {post.cover_image ? (
          <Image source={{ uri: post.cover_image }} style={styles.cover} resizeMode="cover" />
        ) : null}

        <Text style={styles.body}>{previewText(post)}</Text>

        {photos.map((photo) => (
          <View key={photo.id}>
            <Image source={{ uri: photo.file }} style={styles.photo} resizeMode="cover" />
            {photo.caption ? <Text style={styles.caption}>{photo.caption}</Text> : null}
          </View>
        ))}

        {(videos.length > 0 || documents.length > 0 || links.length > 0) && (
          <View style={styles.resources}>
            <Text style={styles.resourcesTitle}>Ressources</Text>
            {videos.map((video) => (
              <Resource
                key={`v-${video.id}`}
                icon="▶"
                label={video.title || video.original_filename || 'Vidéo'}
                url={video.file}
              />
            ))}
            {documents.map((doc) => (
              <Resource
                key={`d-${doc.id}`}
                icon="▤"
                label={doc.title || doc.original_filename || 'Document'}
                url={doc.file}
              />
            ))}
            {links.map((link) => (
              <Resource key={`l-${link.id}`} icon="↗" label={link.label || link.url} url={link.url} />
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.gray },
  centered: { alignItems: 'center', justifyContent: 'center', padding: 24 },
  content: { padding: 20, paddingBottom: 40 },

  metaRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  badge: {
    fontSize: 10, fontWeight: '700', letterSpacing: 0.6, color: colors.navy,
    backgroundColor: '#e6eeff', paddingHorizontal: 9, paddingVertical: 4,
    borderRadius: 999, overflow: 'hidden',
  },
  metaTime: { fontSize: 11, color: '#8a909b' },

  title: { fontSize: 20, fontWeight: '700', color: colors.navy, lineHeight: 27 },
  author: { fontSize: 12, color: '#8a909b', marginTop: 6 },
  cover: { width: '100%', height: 190, borderRadius: 11, marginTop: 14 },
  body: { fontSize: 14, color: '#2f3640', lineHeight: 22, marginTop: 16 },
  photo: { width: '100%', height: 200, borderRadius: 10, marginTop: 14 },
  caption: { fontSize: 12, color: '#8a909b', marginTop: 5 },

  resources: {
    marginTop: 22, backgroundColor: colors.white, borderRadius: 12, padding: 16,
  },
  resourcesTitle: { fontSize: 13, fontWeight: '700', color: colors.navy, marginBottom: 10 },
  resource: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    paddingVertical: 11, borderTopWidth: 1, borderTopColor: '#eef1f6',
  },
  resourceIcon: { fontSize: 15, color: colors.navyLight, width: 22 },
  resourceLabel: { flex: 1, fontSize: 13, color: '#2f3640' },
  resourceOpen: { fontSize: 12, fontWeight: '700', color: colors.navyLight },

  stateText: { color: '#5c6470', fontSize: 14, textAlign: 'center' },
  backButton: { marginTop: 18, paddingVertical: 12, paddingHorizontal: 26, backgroundColor: colors.navy, borderRadius: 8 },
  backText: { color: colors.white, fontWeight: '700' },
});
