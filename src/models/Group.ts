import { Schema, model, Document } from 'mongoose';

export interface IGroup extends Document {
  chatId: number;
  title: string;
  isActive: boolean;
  joinedAt: Date;
  memberCount: number;
  settings: {
    aiEnabled: boolean;
    mediaEnabled: boolean;
    voiceEnabled: boolean;
    welcomeMessage: string;
    language: string;
  };
  stats: {
    totalMessages: number;
    aiRequests: number;
    mediaDownloads: number;
    voiceRequests: number;
  };
}

const groupSchema = new Schema<IGroup>({
  chatId: { type: Number, required: true, unique: true, index: true },
  title: { type: String, default: '' },
  isActive: { type: Boolean, default: true },
  joinedAt: { type: Date, default: Date.now },
  memberCount: { type: Number, default: 0 },
  settings: {
    aiEnabled: { type: Boolean, default: true },
    mediaEnabled: { type: Boolean, default: true },
    voiceEnabled: { type: Boolean, default: true },
    welcomeMessage: { type: String, default: 'مرحباً بك! 👋' },
    language: { type: String, default: 'ar' },
  },
  stats: {
    totalMessages: { type: Number, default: 0 },
    aiRequests: { type: Number, default: 0 },
    mediaDownloads: { type: Number, default: 0 },
    voiceRequests: { type: Number, default: 0 },
  },
});

export const Group = model<IGroup>('Group', groupSchema);
