import type { TDropdownProps } from "../types";

export type MemberDropdownProps = TDropdownProps & {
  button?: React.ReactNode;
  dropdownArrow?: boolean;
  dropdownArrowClassName?: string;
  placeholder?: string;
  tooltipContent?: string;
  onClose?: () => void;
  showUserDetails?: boolean;
  /**
   * "hanya diri sendiri": opsi dropdown disaring ke satu id ini saja.
   * Dipakai layar buat/ubah work item saat pembukanya staf — server tetap
   * pemegang keputusan (gerbang hierarki), ini cuma supaya daftarnya tidak
   * menampilkan orang yang pasti ditolak.
   */
  hanyaDiriSendiri?: string | null;
  /**
   * Selalu sertakan pengguna yang sedang login di daftar opsi, walau ia tidak
   * tercatat sebagai anggota (non-guest) project: misalnya atasan yang masuk
   * lewat jangkauan hierarki. Dipakai lead & anggota module.
   */
  sertakanDiriSendiri?: boolean;
  /**
   * Avatar anggota terpilih membuka kartu profilnya saat diklik (seperti di
   * chat); sisa tombol tetap membuka pemilih. Nyalakan di tempat yang
   * menampilkan orang sebagai data (tabel, kartu, daftar), bukan di formulir.
   */
  showProfileCard?: boolean;
} & (
    | {
        multiple: false;
        onChange: (val: string | null) => void;
        value: string | null;
      }
    | {
        multiple: true;
        onChange: (val: string[]) => void;
        value: string[];
      }
  );
