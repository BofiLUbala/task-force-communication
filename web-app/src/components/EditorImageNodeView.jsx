import { useRef, useState } from 'react';
import { NodeViewWrapper } from '@tiptap/react';

const SIZES = [
  { value: 25, label: '25%' },
  { value: 50, label: '50%' },
  { value: 75, label: '75%' },
  { value: 100, label: '100%' },
];

const ALIGNMENTS = [
  { value: 'left', icon: 'format_align_left', label: 'Aligner à gauche' },
  { value: 'center', icon: 'format_align_center', label: 'Centrer' },
  { value: 'right', icon: 'format_align_right', label: 'Aligner à droite' },
];

export default function EditorImageNodeView({ node, updateAttributes, deleteNode, selected }) {
  const { src, alt, width, align } = node.attrs;
  const wrapRef = useRef(null);
  const [resizing, setResizing] = useState(false);

  function startResize(e) {
    e.preventDefault();
    const wrapEl = wrapRef.current;
    const container = wrapEl?.closest('.rte-content');
    if (!container) return;

    const containerWidth = container.clientWidth;
    const startX = e.clientX;
    const startWidthPct = width || 100;
    setResizing(true);

    function onMove(moveEvent) {
      const deltaPx = moveEvent.clientX - startX;
      const deltaPct = (deltaPx / containerWidth) * 100;
      const next = Math.min(100, Math.max(10, Math.round(startWidthPct + deltaPct)));
      updateAttributes({ width: next });
    }
    function onUp() {
      setResizing(false);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }

  return (
    <NodeViewWrapper
      className={`rte-image-wrap align-${align || 'left'} ${selected ? 'is-selected' : ''} ${resizing ? 'is-resizing' : ''}`}
      ref={wrapRef}
      style={{ width: `${width || 100}%` }}
    >
      <img src={src} alt={alt || ''} draggable={false} />

      {selected && (
        <div className="rte-image-toolbar" contentEditable={false}>
          {ALIGNMENTS.map((a) => (
            <button
              key={a.value}
              type="button"
              className={align === a.value || (!align && a.value === 'left') ? 'active' : ''}
              title={a.label}
              onMouseDown={(e) => { e.preventDefault(); updateAttributes({ align: a.value }); }}
            >
              <span className="material-symbols-outlined">{a.icon}</span>
            </button>
          ))}
          <span className="rte-image-toolbar-sep" />
          {SIZES.map((s) => (
            <button
              key={s.value}
              type="button"
              className={`rte-image-size-btn ${width === s.value ? 'active' : ''}`}
              title={`Taille ${s.label}`}
              onMouseDown={(e) => { e.preventDefault(); updateAttributes({ width: s.value }); }}
            >
              {s.label}
            </button>
          ))}
          <span className="rte-image-toolbar-sep" />
          <button
            type="button"
            className="rte-image-remove"
            title="Supprimer l'image"
            onMouseDown={(e) => { e.preventDefault(); deleteNode(); }}
          >
            <span className="material-symbols-outlined">delete</span>
          </button>
        </div>
      )}

      {selected && (
        <div
          className="rte-image-resize-handle"
          onMouseDown={startResize}
          title="Glisser pour redimensionner"
        />
      )}
    </NodeViewWrapper>
  );
}
