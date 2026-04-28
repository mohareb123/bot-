import { Schema, model, Document } from 'mongoose';

export interface IUser extends Document {
  telegramId: number;
  username: string;
  firstName: string;
  lastName: string;
  role: 'user' | 'admin' | 'superadmin' | 'banned';
  requestCount: number;
  lastRequestTime: Date;
  totalRequests: number;
  joinedAt: Date;
  lastActive: Date;
  settings: {
    language: string;
    ttsVoice: string;
    imageQuality: string;
    notifications: boolean;
  };
  googleLinked: boolean;
  googleCookies: string;
}

const userSchema = new Schema<IUser>({
  telegramId: { type: Number, required: true, unique: true, index: true },
  username: { type: String, default: '' },
  firstName: { type: String, default: '' },
  lastName: { type: String, default: '' },
  role: { type: String, enum: ['user', 'admin', 'superadmin', 'banned'], default: 'user' },
  requestCount: { type: Number, default: 0 },
  lastRequestTime: { type: Date, default: Date.now },
  totalRequests: { type: Number, default: 0 },
  joinedAt: { type: Date, default: Date.now },
  lastActive: { type: Date, default: Date.now },
  settings: {
    language: { type: String, default: 'ar' },
    ttsVoice: { type: String, default: 'ar-EG-ShakirNeural' },
    imageQuality: { type: String, default: 'high' },
    notifications: { type: Boolean, default: true },
  },
  googleLinked: { type: Boolean, default: false },
  googleCookies: { type: String, default: '' },
});

userSchema.methods.isAdmin = function (): boolean {
  return this.role === 'admin' || this.role === 'superadmin';
};

userSchema.methods.isBanned = function (): boolean {
  return this.role === 'banned';
};

export const User = model<IUser>('User', userSchema);
