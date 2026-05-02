import React, { useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import type { DragStartEvent, DragEndEvent } from '@dnd-kit/core';
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import type { ApplicationOut } from '../api';
import { Briefcase } from 'lucide-react';

interface KanbanBoardProps {
  applications: ApplicationOut[];
  onStatusChange: (id: number, newStatus: string) => void;
  onCardClick: (id: number) => void;
}

const COLUMNS = [
  { id: 'wishlist', title: 'Wishlist' },
  { id: 'applied', title: 'Applied' },
  { id: 'interview', title: 'Interview' },
  { id: 'offer', title: 'Offer' },
  { id: 'rejected', title: 'Rejected' },
];

const KanbanCard = ({ application, onClick }: { application: ApplicationOut, onClick?: (id: number) => void }) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: application.id,
    data: {
      type: 'Task',
      application,
    },
  });

  const style = {
    transition,
    transform: CSS.Translate.toString(transform),
    cursor: isDragging ? 'grabbing' : 'pointer',
  };

  if (isDragging) {
    return (
      <div
        ref={setNodeRef}
        style={style}
        className="kanban-card dragging"
      />
    );
  }

  const score = Math.round((application.match_score || 0) * 100);
  const scoreColor = score > 70 ? '#6366f1' : score > 40 ? '#fbbf24' : '#f87171';

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="kanban-card"
      onClick={() => onClick && onClick(application.id)}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', gap: '8px' }}>
        <div style={{ fontSize: '0.85rem', fontWeight: '600', color: 'white', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {application.job_title || 'Untitled'}
        </div>
        <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: scoreColor }}>
          {score}%
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>
        <Briefcase size={12} />
        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {application.company || 'Unknown'}
        </span>
      </div>
    </div>
  );
};

const KanbanColumn = ({ id, title, applications, onCardClick }: { id: string, title: string, applications: ApplicationOut[], onCardClick: (id: number) => void }) => {
  const { setNodeRef } = useSortable({
    id,
    data: {
      type: 'Column',
    },
  });

  return (
    <div className="kanban-column">
      <div className="column-header">
        <h3>{title}</h3>
        <span className="count">{applications.length}</span>
      </div>
      <div ref={setNodeRef} className="column-content">
        <SortableContext items={applications.map(a => a.id)} strategy={verticalListSortingStrategy}>
          {applications.map(app => (
            <KanbanCard key={app.id} application={app} onClick={onCardClick} />
          ))}
        </SortableContext>
      </div>
    </div>
  );
};

export const KanbanBoard = ({ applications, onStatusChange, onCardClick }: KanbanBoardProps) => {
  const [activeId, setActiveId] = React.useState<number | null>(null);
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const groupedApplications = useMemo(() => {
    return COLUMNS.reduce((acc, col) => {
      acc[col.id] = applications.filter(app => app.kanban_status === col.id);
      return acc;
    }, {} as Record<string, ApplicationOut[]>);
  }, [applications]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveId(event.active.id as number);
  };

  const handleDragOver = (event: DragOverEvent) => {
    // We can use handleDragOver if we want to show visual feedback during drag
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over) {
      setActiveId(null);
      return;
    }

    const activeApp = applications.find(a => a.id === active.id);
    if (!activeApp) {
      setActiveId(null);
      return;
    }

    const overId = over.id.toString();
    
    // Logic to find target status
    let newStatus: string | null = null;
    
    // 1. Is 'over' a column?
    if (COLUMNS.some(c => c.id === overId)) {
      newStatus = overId;
    } else {
      // 2. Is 'over' a card? If so, get its column
      const overApp = applications.find(a => a.id === Number(overId));
      if (overApp) {
        newStatus = overApp.kanban_status;
      }
    }

    if (newStatus && activeApp.kanban_status !== newStatus) {
      onStatusChange(activeApp.id, newStatus);
    }

    setActiveId(null);
  };

  return (
    <div className="kanban-container">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="kanban-grid">
          {COLUMNS.map(col => (
            <KanbanColumn
              key={col.id}
              id={col.id}
              title={col.title}
              applications={groupedApplications[col.id] || []}
              onCardClick={onCardClick}
            />
          ))}
        </div>
        <DragOverlay dropAnimation={null}>
          {activeId ? (
            <div style={{ width: '250px' }}>
              <KanbanCard application={applications.find(a => a.id === activeId)!} />
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </div>
  );
};

export default KanbanBoard;
