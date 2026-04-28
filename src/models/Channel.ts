import { Schema, model, Document } from 'mongoose';

export interface IChannel extends Document {
  channelId: string;
  username: string;
  title: string;
  isRequired: boolean;
  addedAt: Date;
  subscriberCount: number;
}

const channelSchema = new Schema<IChannel>({
  channelId: { type: String, default: '' },
  username: { type: String, required: true, unique: true },
  title: { type: String, default: '' },
  isRequired: { type: Boolean, default: true },
  addedAt: { type: Date, default: Date.now },
  subscriberCount: { type: Number, default: 0 },
});

export const Channel = model<IChannel>('Channel', channelSchema);
