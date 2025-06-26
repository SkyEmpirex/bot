
import discord
from discord.ext import commands
import sqlite3
import random
import string
from datetime import datetime
import asyncio

# Bot ayarları
BOT_TOKEN = "MTM4MTU3NzY2MTI0MzE5OTU2OQ.GFiW5e.LTL_Pmmc3KP92ofAOR_1Pp1UpJll31ckyAu8d8"
ADMIN_ROLE = "Admin"
PAPARA_NO = "1232057512"

# Bot oluştur
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Veritabanı bağlantısı
def init_db():
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # Ürünler tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT
        )
    ''')

    # Siparişler tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            username TEXT NOT NULL,
            product_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Varsayılan ürünleri ekle
    products = [
        ("VIP KIT", 25, "VIP üyelik paketi - Özel avantajlar"),
        ("VIP+ KIT", 50, "VIP+ üyelik paketi - Tüm avantajlar"),
        ("LVIP KIT", 75, "LVIP paketi - Temel avantajlar - Yeni Sezon İndirimi"),
        ("LVIP+ KIT", 100, "LVIP+ üyelik paketi - En iyi avantajlar - Yeni Sezon İndirimi"),
        ("MVIP KIT", 125, "MVIP üyelik paketi - Özel avantajlar - Yeni Sezon İndirimi"),
        ("MVIP+ KIT", 200, "MVIP+ üyelik paketi - Tüm avantajlar - Yeni Sezon İndirimi")
    ]

    cursor.executemany('INSERT OR IGNORE INTO products (name, price, description) VALUES (?, ?, ?)', products)
    conn.commit()
    conn.close()

# Sipariş kodu oluştur
def generate_order_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Bot hazır olduğunda
@bot.event
async def on_ready():
    print(f'{bot.user} olarak giriş yapıldı!')
    init_db()

# Market komutları
@bot.command(name='market')
async def market(ctx):
    """Market ürünlerini gösterir"""
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, price, description FROM products')
    products = cursor.fetchall()
    conn.close()

    if not products:
        await ctx.send("Henüz ürün bulunmamaktadır.")
        return

    embed = discord.Embed(
        title="🛒 TüccarKöylü Market",
        description="Mevcut ürünlerimiz:",
        color=0x00ff00
    )

    # Maksimum 20 field ekle (güvenli limit)
    for product in products[:20]:
        embed.add_field(
            name=f"{product[0]} - {product[1]}TL",
            value=product[2],
            inline=False
        )

    embed.add_field(
        name="📝 Nasıl Satın Alırım?",
        value="Ürün satın almak için: `!satinal {ürün adı}`\nÖrnek: `!satinal VIP KIT`",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command(name='satinal')
async def buy_product(ctx, *, product_name=None):
    """Ürün satın alma"""
    if not product_name:
        await ctx.send("❌ Lütfen satın almak istediğiniz ürünü belirtin!\nÖrnek: `!satinal VIP KIT`")
        return

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    # Ürünü kontrol et
    cursor.execute('SELECT name, price FROM products WHERE LOWER(name) = LOWER(?)', (product_name,))
    product = cursor.fetchone()

    if not product:
        await ctx.send(f"❌ '{product_name}' adında bir ürün bulunamadı!\n`!market` komutu ile mevcut ürünleri görebilirsiniz.")
        conn.close()
        return

    # Sipariş kodu oluştur
    order_code = generate_order_code()

    # Siparişi veritabanına ekle
    cursor.execute('''
        INSERT INTO orders (order_code, user_id, username, product_name, price)
        VALUES (?, ?, ?, ?, ?)
    ''', (order_code, str(ctx.author.id), str(ctx.author), product[0], product[1]))

    conn.commit()
    conn.close()

    # Satın alma talimatları
    embed = discord.Embed(
        title="💳 Ödeme Talimatları",
        description=f"**{product[0]}** - {product[1]}TL",
        color=0xffa500
    )

    embed.add_field(
        name="1️⃣ Papara'ya Git",
        value=f"Para Gönder Kısmından Papara No/IBAN seçeneğine tıkla ve Papara Numarası kısmına {PAPARA_NO} yaz ardından DEVAM ET seçeneğine tıkla",
        inline=False
    )

    embed.add_field(
        name="2️⃣ Açıklama Kısmına Yazın",
        value=f"**{order_code}**",
        inline=False
    )

    embed.add_field(
        name="3️⃣ Tutar",
        value=f"**{product[1]} TL**",
        inline=False
    )

    embed.add_field(
        name="4️⃣ Sipariş Takibi",
        value=f"`!siparis_durumu {order_code}`",
        inline=False
    )

    embed.add_field(
        name="⚠️ Önemli",
        value="Ödeme yaparken açıklama kısmına sipariş kodunu yazmayı unutmayın!\nSipariş kodu: **" + order_code + "**",
        inline=False
    )

    embed.set_footer(text=f"Sipariş Kodu: {order_code}")

    await ctx.send(embed=embed)

@bot.command(name='siparis_durumu')
async def order_status(ctx, order_code=None):
    """Sipariş durumunu kontrol et"""
    if not order_code:
        await ctx.send("❌ Sipariş kodunu belirtin!\nÖrnek: `!siparis_durumu ABC12345`")
        return

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT product_name, price, status, created_at 
        FROM orders 
        WHERE order_code = ? AND user_id = ?
    ''', (order_code.upper(), str(ctx.author.id)))

    order = cursor.fetchone()
    conn.close()

    if not order:
        await ctx.send(f"❌ '{order_code}' sipariş kodu bulunamadı veya size ait değil!")
        return

    status_colors = {
        'pending': 0xffa500,
        'completed': 0x00ff00,
        'cancelled': 0xff0000
    }

    status_texts = {
        'pending': '⏳ Beklemede',
        'completed': '✅ Tamamlandı',
        'cancelled': '❌ İptal Edildi'
    }

    embed = discord.Embed(
        title="📋 Sipariş Durumu",
        color=status_colors.get(order[2], 0x808080)
    )

    embed.add_field(name="Ürün", value=order[0], inline=True)
    embed.add_field(name="Fiyat", value=f"{order[1]} TL", inline=True)
    embed.add_field(name="Durum", value=status_texts.get(order[2], order[2]), inline=True)
    embed.add_field(name="Sipariş Tarihi", value=order[3][:19], inline=False)

    embed.set_footer(text=f"Sipariş Kodu: {order_code.upper()}")

    await ctx.send(embed=embed)

# Admin komutları
@bot.command(name='admin_panel')
@commands.has_role(ADMIN_ROLE)
async def admin_panel(ctx):
    """Admin paneli"""
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT order_code, username, product_name, price, created_at
        FROM orders 
        WHERE status = 'pending'
        ORDER BY created_at DESC
    ''')

    pending_orders = cursor.fetchall()
    conn.close()

    if not pending_orders:
        await ctx.send("✅ Bekleyen sipariş bulunmamaktadır.")
        return

    # Siparişleri sayfalara böl (her sayfada 10 sipariş)
    page_size = 10
    total_pages = (len(pending_orders) + page_size - 1) // page_size
    
    for page in range(total_pages):
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(pending_orders))
        page_orders = pending_orders[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"🔧 Admin Panel - Bekleyen Siparişler (Sayfa {page + 1}/{total_pages})",
            color=0x0099ff
        )

        for order in page_orders:
            embed.add_field(
                name=f"Kod: {order[0]}",
                value=f"**Kullanıcı:** {order[1]}\n**Ürün:** {order[2]}\n**Fiyat:** {order[3]}TL\n**Tarih:** {order[4][:19]}",
                inline=False
            )

        embed.add_field(
            name="📝 Komutlar",
            value="`!onayla {sipariş_kodu}` - Siparişi onayla\n`!iptal {sipariş_kodu}` - Siparişi iptal et\n`!siparisler` - Tüm siparişleri listele",
            inline=False
        )

        await ctx.send(embed=embed)

@bot.command(name='onayla')
@commands.has_role(ADMIN_ROLE)
async def approve_order(ctx, order_code=None):
    """Siparişi onayla"""
    if not order_code:
        await ctx.send("❌ Sipariş kodunu belirtin!\nÖrnek: `!onayla ABC12345`")
        return

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    cursor.execute('SELECT user_id, username, product_name FROM orders WHERE order_code = ? AND status = "pending"', (order_code.upper(),))
    order = cursor.fetchone()

    if not order:
        await ctx.send(f"❌ '{order_code}' kodlu bekleyen sipariş bulunamadı!")
        conn.close()
        return

    cursor.execute('UPDATE orders SET status = "completed" WHERE order_code = ?', (order_code.upper(),))
    conn.commit()
    conn.close()

    try:
        user = await bot.fetch_user(int(order[0]))
        embed = discord.Embed(
            title="✅ Sipariş Onaylandı!",
            description=f"**{order[2]}** siparişiniz başarıyla onaylandı!",
            color=0x00ff00
        )
        embed.add_field(name="Sipariş Kodu", value=order_code.upper(), inline=False)
        await user.send(embed=embed)
    except:
        pass

    await ctx.send(f"✅ **{order_code.upper()}** kodlu sipariş onaylandı!\nKullanıcı: {order[1]}\nÜrün: {order[2]}")

@bot.command(name='iptal')
@commands.has_role(ADMIN_ROLE)
async def cancel_order(ctx, order_code=None):
    """Siparişi iptal et"""
    if not order_code:
        await ctx.send("❌ Sipariş kodunu belirtin!\nÖrnek: `!iptal ABC12345`")
        return

    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    cursor.execute('SELECT user_id, username, product_name FROM orders WHERE order_code = ? AND status = "pending"', (order_code.upper(),))
    order = cursor.fetchone()

    if not order:
        await ctx.send(f"❌ '{order_code}' kodlu bekleyen sipariş bulunamadı!")
        conn.close()
        return

    cursor.execute('UPDATE orders SET status = "cancelled" WHERE order_code = ?', (order_code.upper(),))
    conn.commit()
    conn.close()

    try:
        user = await bot.fetch_user(int(order[0]))
        embed = discord.Embed(
            title="❌ Sipariş İptal Edildi",
            description=f"**{order[2]}** siparişiniz iptal edildi.",
            color=0xff0000
        )
        embed.add_field(name="Sipariş Kodu", value=order_code.upper(), inline=False)
        await user.send(embed=embed)
    except:
        pass

    await ctx.send(f"❌ **{order_code.upper()}** kodlu sipariş iptal edildi!\nKullanıcı: {order[1]}\nÜrün: {order[2]}")

@bot.command(name='siparisler')
@commands.has_role(ADMIN_ROLE)
async def all_orders(ctx, status=None):
    """Tüm siparişleri listele"""
    conn = sqlite3.connect('market.db')
    cursor = conn.cursor()

    if status:
        cursor.execute('SELECT order_code, username, product_name, price, status, created_at FROM orders WHERE status = ? ORDER BY created_at DESC', (status,))
    else:
        cursor.execute('SELECT order_code, username, product_name, price, status, created_at FROM orders ORDER BY created_at DESC')

    orders = cursor.fetchall()
    conn.close()

    if not orders:
        await ctx.send("📝 Sipariş bulunamadı.")
        return

    status_emojis = {
        'pending': '⏳',
        'completed': '✅',
        'cancelled': '❌'
    }

    # Siparişleri sayfalara böl (her sayfada 15 sipariş)
    page_size = 15
    total_pages = (len(orders) + page_size - 1) // page_size
    
    for page in range(total_pages):
        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(orders))
        page_orders = orders[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"📋 Tüm Siparişler (Sayfa {page + 1}/{total_pages})",
            color=0x0099ff
        )

        for order in page_orders:
            status_emoji = status_emojis.get(order[4], '❓')
            embed.add_field(
                name=f"{status_emoji} {order[0]}",
                value=f"**Kullanıcı:** {order[1]}\n**Ürün:** {order[2]}\n**Fiyat:** {order[3]}TL\n**Tarih:** {order[5][:19]}",
                inline=True
            )

        await ctx.send(embed=embed)

# Hata yönetimi
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("❌ Bu komutu kullanmak için yeterli yetkiniz yok!")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        print(f"Hata: {error}")

# Yardım komutu
@bot.command(name='yardim')
async def help_command(ctx):
    """Yardım menüsü"""
    embed = discord.Embed(
        title="🤖 TüccarKöylü Bot Yardım",
        description="Mevcut komutlar:",
        color=0x0099ff
    )

    embed.add_field(
        name="👥 Genel Komutlar",
        value="`!market` - Mevcut ürünleri göster\n`!satinal {ürün}` - Ürün satın al\n`!siparis_durumu {kod}` - Sipariş durumunu kontrol et\n`!yardim` - Bu yardım menüsü",
        inline=False
    )

    if any(role.name == ADMIN_ROLE for role in ctx.author.roles):
        embed.add_field(
            name="🔧 Admin Komutları",
            value="`!admin_panel` - Admin paneli\n`!onayla {kod}` - Siparişi onayla\n`!iptal {kod}` - Siparişi iptal et\n`!siparisler` - Tüm siparişleri listele",
            inline=False
        )

    await ctx.send(embed=embed)

# Botu çalıştır
if __name__ == "__main__":
    from keep_alive import keep_alive
    keep_alive()
    bot.run(BOT_TOKEN)
