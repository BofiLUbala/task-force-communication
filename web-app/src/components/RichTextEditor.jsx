import { useEffect, useRef, useState } from 'react';
import { EditorContent, ReactNodeViewRenderer, useEditor } from '@tiptap/react';
import { mergeAttributes } from '@tiptap/core';
import StarterKit from '@tiptap/starter-kit';
import TextAlign from '@tiptap/extension-text-align';
import { TextStyle } from '@tiptap/extension-text-style';
import Color from '@tiptap/extension-color';
import Highlight from '@tiptap/extension-highlight';
import Image from '@tiptap/extension-image';
import Placeholder from '@tiptap/extension-placeholder';
import client from '../api/client';
import usePreferences from '../hooks/usePreferences';
import EditorImageNodeView from './EditorImageNodeView';
import './RichTextEditor.css';

const TEXT_COLORS = ['#0d1c2e', '#002f6a', '#ba1a1a', '#176c36', '#705d00'];
const HIGHLIGHT_COLORS = ['#fed721', '#a7f3d0', '#fecaca', '#bfdbfe'];

const ResizableImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      width: {
        default: 100,
        parseHTML: (element) => Number(element.getAttribute('data-width') || element.getAttribute('width')) || 100,
      },
      align: {
        default: 'left',
        parseHTML: (element) => element.getAttribute('data-align') || element.getAttribute('align') || 'left',
      },
    };
  },
  renderHTML({ HTMLAttributes }) {
    const { width = 100, align = 'left', style, ...attributes } = HTMLAttributes;
    const margins = {
      left: 'margin-left:0;margin-right:auto',
      center: 'margin-left:auto;margin-right:auto',
      right: 'margin-left:auto;margin-right:0',
    }[align] || 'margin-left:0;margin-right:auto';
    return ['img', mergeAttributes(this.options.HTMLAttributes, attributes, {
      'data-width': width,
      'data-align': align,
      style: `display:block;width:${width}%;max-width:100%;height:auto;${margins};${style || ''}`,
    })];
  },
  addNodeView() {
    return ReactNodeViewRenderer(EditorImageNodeView);
  },
});

export default function RichTextEditor({ id, value, onChange, placeholder }) {
  const { tr } = usePreferences();
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        link: { openOnClick: false, autolink: true },
        bulletList: { keepMarks: true, keepAttributes: true },
        orderedList: { keepMarks: true, keepAttributes: true },
      }),
      TextStyle,
      Color,
      Highlight.configure({ multicolor: true }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      ResizableImage,
      Placeholder.configure({ placeholder: placeholder || '' }),
    ],
    content: value || '',
    onUpdate: ({ editor: current }) => onChange(current.getHTML()),
    editorProps: {
      attributes: { id, class: 'rte-content', 'aria-label': placeholder || '' },
    },
  });

  useEffect(() => {
    if (editor && !editor.isDestroyed && value !== editor.getHTML() && !editor.isFocused) {
      editor.commands.setContent(value || '', { emitUpdate: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, editor]);

  useEffect(() => () => editor?.destroy(), [editor]);

  if (!editor) return null;

  function toggleLink() {
    const previous = editor.getAttributes('link').href;
    // eslint-disable-next-line no-alert
    const url = window.prompt(tr('Adresse du lien (laisser vide pour retirer)', 'Link URL (leave blank to remove)'), previous || 'https://');
    if (url === null) return;
    if (url.trim() === '') {
      editor.chain().focus().unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange('link').setLink({ href: url.trim() }).run();
  }

function insertImage() {
    setUploadError('');
    fileInputRef.current?.click();
  }

  async function handleImageFileChange(e) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;

    setUploading(true);
    setUploadError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const { data } = await client.post('/editor-images/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      editor.chain().focus().setImage({ src: data.file }).run();
    } catch {
      setUploadError(tr('Échec de l’envoi de l’image. Réessayez.', 'Image upload failed. Please try again.'));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="rte">
      <div className="rte-toolbar" role="toolbar" aria-label={tr('Mise en forme du texte', 'Text formatting')}>
        <div className="rte-group">
          <button type="button" className={editor.isActive('bold') ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleBold().run(); }} title={tr('Gras', 'Bold')}>
            <span className="material-symbols-outlined">format_bold</span>
          </button>
          <button type="button" className={editor.isActive('italic') ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleItalic().run(); }} title={tr('Italique', 'Italic')}>
            <span className="material-symbols-outlined">format_italic</span>
          </button>
          <button type="button" className={editor.isActive('underline') ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleUnderline().run(); }} title={tr('Souligné', 'Underline')}>
            <span className="material-symbols-outlined">format_underlined</span>
          </button>
          <button type="button" className={editor.isActive('strike') ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleStrike().run(); }} title={tr('Barré', 'Strikethrough')}>
            <span className="material-symbols-outlined">strikethrough_s</span>
          </button>
        </div>

        <div className="rte-divider" />

        <div className="rte-group">
          <button type="button" className={editor.isActive('heading', { level: 2 }) ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleHeading({ level: 2 }).run(); }} title={tr('Titre', 'Heading')}>H2</button>
          <button type="button" className={editor.isActive('heading', { level: 3 }) ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleHeading({ level: 3 }).run(); }} title={tr('Sous-titre', 'Subheading')}>H3</button>
        </div>

        <div className="rte-divider" />

        <div className="rte-group">
          <button type="button" className={editor.isActive('bulletList') ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleBulletList().run(); }} title={tr('Liste à puces', 'Bullet list')}>
            <span className="material-symbols-outlined">format_list_bulleted</span>
          </button>
          <button type="button" className={editor.isActive('orderedList') ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleOrderedList().run(); }} title={tr('Liste numérotée', 'Numbered list')}>
            <span className="material-symbols-outlined">format_list_numbered</span>
          </button>
          <button type="button" className={editor.isActive('blockquote') ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleBlockquote().run(); }} title={tr('Citation', 'Quote')}>
            <span className="material-symbols-outlined">format_quote</span>
          </button>
        </div>

        <div className="rte-divider" />

        <div className="rte-group">
          <button type="button" className={editor.isActive({ textAlign: 'left' }) ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().setTextAlign('left').run(); }} title={tr('Aligner à gauche', 'Align left')}>
            <span className="material-symbols-outlined">format_align_left</span>
          </button>
          <button type="button" className={editor.isActive({ textAlign: 'center' }) ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().setTextAlign('center').run(); }} title={tr('Centrer', 'Align center')}>
            <span className="material-symbols-outlined">format_align_center</span>
          </button>
          <button type="button" className={editor.isActive({ textAlign: 'right' }) ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().setTextAlign('right').run(); }} title={tr('Aligner à droite', 'Align right')}>
            <span className="material-symbols-outlined">format_align_right</span>
          </button>
          <button type="button" className={editor.isActive({ textAlign: 'justify' }) ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().setTextAlign('justify').run(); }} title={tr('Justifier', 'Justify')}>
            <span className="material-symbols-outlined">format_align_justify</span>
          </button>
        </div>

        <div className="rte-divider" />

        <div className="rte-group">
          <button type="button" className={editor.isActive('link') ? 'active' : ''} onMouseDown={(e) => { e.preventDefault(); toggleLink(); }} title={tr('Insérer un lien', 'Insert link')}>
            <span className="material-symbols-outlined">link</span>
          </button>
          <button type="button" disabled={uploading} onMouseDown={(e) => { e.preventDefault(); insertImage(); }} title={tr('Insérer une image', 'Insert image')}>
            <span className="material-symbols-outlined">{uploading ? 'progress_activity' : 'image'}</span>
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageFileChange}
            style={{ display: 'none' }}
          />
        </div>

        <div className="rte-divider" />

        <div className="rte-group rte-swatches" title={tr('Couleur du texte', 'Text color')}>
          {TEXT_COLORS.map((c) => (
            <button
              key={c}
              type="button"
              className="rte-swatch"
              style={{ '--swatch': c }}
              onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().setColor(c).run(); }}
              aria-label={`${tr('Couleur', 'Color')} ${c}`}
            />
          ))}
          <button type="button" className="rte-swatch-reset" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().unsetColor().run(); }} title={tr('Réinitialiser la couleur', 'Reset color')}>
            <span className="material-symbols-outlined">format_color_reset</span>
          </button>
        </div>

        <div className="rte-group rte-swatches" title={tr('Surlignage', 'Highlight')}>
          {HIGHLIGHT_COLORS.map((c) => (
            <button
              key={c}
              type="button"
              className="rte-swatch rte-swatch-highlight"
              style={{ '--swatch': c }}
              onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().toggleHighlight({ color: c }).run(); }}
              aria-label={`${tr('Surligner', 'Highlight')} ${c}`}
            />
          ))}
          <button type="button" className="rte-swatch-reset" onMouseDown={(e) => { e.preventDefault(); editor.chain().focus().unsetHighlight().run(); }} title={tr('Retirer le surlignage', 'Remove highlight')}>
            <span className="material-symbols-outlined">format_color_reset</span>
          </button>
        </div>
      </div>
      {uploadError && <div className="rte-error">{uploadError}</div>}
      <EditorContent editor={editor} />
    </div>
  );
}
