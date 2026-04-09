/*
  BlogDB 表结构 + 字段说明（SQL Server）
  ======================================
  与 backend/app/models 中 ORM 对齐。

  使用前提：已执行同目录 init.sql，当前可 USE 到 BlogDB。

  行为说明：
  - 建表：IF OBJECT_ID … IS NULL 则 CREATE，已存在则跳过，不破坏数据。
  - 说明：通过扩展属性 MS_Description 写入；已存在则 sp_update，否则 sp_add，可重复执行。

  在 SSMS 中连接实例后，选中本文件「执行」即可。
*/

USE BlogDB;
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

/* ========== dbo.users ========== */
IF OBJECT_ID(N'dbo.users', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.users (
        id              INT            IDENTITY(1, 1) NOT NULL,
        username        NVARCHAR(64)   NOT NULL,
        hashed_password NVARCHAR(255)  NOT NULL,
        is_active       BIT            NOT NULL CONSTRAINT DF_users_is_active DEFAULT (1),
        created_at      DATETIME2(3)   NOT NULL,
        CONSTRAINT PK_users PRIMARY KEY CLUSTERED (id),
        CONSTRAINT UQ_users_username UNIQUE (username)
    );
END
GO

/* ========== dbo.categories ========== */
IF OBJECT_ID(N'dbo.categories', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.categories (
        id         INT            IDENTITY(1, 1) NOT NULL,
        name       NVARCHAR(128)  NOT NULL,
        slug       NVARCHAR(128)  NOT NULL,
        created_at DATETIME2(3)   NOT NULL,
        updated_at DATETIME2(3)   NOT NULL,
        CONSTRAINT PK_categories PRIMARY KEY CLUSTERED (id),
        CONSTRAINT UQ_categories_slug UNIQUE (slug)
    );
END
GO

/* ========== dbo.tags ========== */
IF OBJECT_ID(N'dbo.tags', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.tags (
        id         INT           IDENTITY(1, 1) NOT NULL,
        name       NVARCHAR(64)  NOT NULL,
        slug       NVARCHAR(64)  NOT NULL,
        created_at DATETIME2(3)  NOT NULL,
        CONSTRAINT PK_tags PRIMARY KEY CLUSTERED (id),
        CONSTRAINT UQ_tags_slug UNIQUE (slug)
    );
END
GO

/* ========== dbo.posts ========== */
IF OBJECT_ID(N'dbo.posts', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.posts (
        id               INT            IDENTITY(1, 1) NOT NULL,
        title            NVARCHAR(255)  NOT NULL,
        slug             NVARCHAR(255)  NOT NULL,
        excerpt          NVARCHAR(500)  NULL,
        content          NVARCHAR(MAX)  NOT NULL,
        published        BIT            NOT NULL CONSTRAINT DF_posts_published DEFAULT (0),
        cover_image_url  NVARCHAR(512)  NULL,
        created_at       DATETIME2(3)   NOT NULL,
        updated_at       DATETIME2(3)   NOT NULL,
        author_id        INT            NULL,
        category_id      INT            NULL,
        CONSTRAINT PK_posts PRIMARY KEY CLUSTERED (id),
        CONSTRAINT UQ_posts_slug UNIQUE (slug)
    );
    CREATE NONCLUSTERED INDEX IX_posts_author_id ON dbo.posts (author_id);
    CREATE NONCLUSTERED INDEX IX_posts_category_id ON dbo.posts (category_id);

    ALTER TABLE dbo.posts WITH NOCHECK
    ADD CONSTRAINT FK_posts_users
        FOREIGN KEY (author_id) REFERENCES dbo.users (id);

    ALTER TABLE dbo.posts WITH NOCHECK
    ADD CONSTRAINT FK_posts_categories
        FOREIGN KEY (category_id) REFERENCES dbo.categories (id);
END
GO

/* ========== dbo.post_tags ========== */
IF OBJECT_ID(N'dbo.post_tags', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.post_tags (
        post_id INT NOT NULL,
        tag_id  INT NOT NULL,
        CONSTRAINT PK_post_tags PRIMARY KEY CLUSTERED (post_id, tag_id),
        CONSTRAINT FK_post_tags_posts FOREIGN KEY (post_id)
            REFERENCES dbo.posts (id) ON DELETE CASCADE,
        CONSTRAINT FK_post_tags_tags FOREIGN KEY (tag_id)
            REFERENCES dbo.tags (id) ON DELETE CASCADE
    );
END
GO

/* ========== dbo.comments ========== */
IF OBJECT_ID(N'dbo.comments', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.comments (
        id          INT            IDENTITY(1, 1) NOT NULL,
        post_id     INT            NOT NULL,
        parent_id   INT            NULL,
        author_name NVARCHAR(128)  NOT NULL,
        content     NVARCHAR(MAX)  NOT NULL,
        created_at  DATETIME2(3)   NOT NULL,
        CONSTRAINT PK_comments PRIMARY KEY CLUSTERED (id),
        CONSTRAINT FK_comments_posts FOREIGN KEY (post_id)
            REFERENCES dbo.posts (id) ON DELETE CASCADE,
        CONSTRAINT FK_comments_parent FOREIGN KEY (parent_id)
            REFERENCES dbo.comments (id)
    );
    CREATE NONCLUSTERED INDEX IX_comments_post_id ON dbo.comments (post_id);
    CREATE NONCLUSTERED INDEX IX_comments_parent_id ON dbo.comments (parent_id);
END
GO

/* ========== MS_Description：表/列说明（可重复执行） ========== */
SET NOCOUNT ON;

DECLARE @d TABLE (
    t SYSNAME NOT NULL,
    c SYSNAME NULL,
    v NVARCHAR(1000) NOT NULL
);

INSERT INTO @d (t, c, v) VALUES
(N'users', NULL, N'后台登录用户，用于管理端认证与文章作者关联'),
(N'users', N'id', N'主键，自增'),
(N'users', N'username', N'登录名，唯一'),
(N'users', N'hashed_password', N'密码哈希（如 bcrypt），不存明文'),
(N'users', N'is_active', N'是否允许登录：1 允许，0 禁止（软禁用）'),
(N'users', N'created_at', N'创建时间'),
(N'categories', NULL, N'文章分类'),
(N'categories', N'id', N'主键，自增'),
(N'categories', N'name', N'分类显示名称'),
(N'categories', N'slug', N'URL 用唯一标识'),
(N'categories', N'created_at', N'创建时间'),
(N'categories', N'updated_at', N'最后更新时间'),
(N'tags', NULL, N'文章标签'),
(N'tags', N'id', N'主键，自增'),
(N'tags', N'name', N'标签显示名称'),
(N'tags', N'slug', N'URL 用唯一标识'),
(N'tags', N'created_at', N'创建时间'),
(N'posts', NULL, N'博文主表'),
(N'posts', N'id', N'主键，自增'),
(N'posts', N'title', N'标题'),
(N'posts', N'slug', N'URL 路径片段，全局唯一'),
(N'posts', N'excerpt', N'摘要/导语，可为空'),
(N'posts', N'content', N'正文（HTML 或 Markdown 等）'),
(N'posts', N'published', N'是否已发布：访客列表仅展示为 1 的文章'),
(N'posts', N'cover_image_url', N'封面图 URL，可为空'),
(N'posts', N'created_at', N'创建时间'),
(N'posts', N'updated_at', N'最后更新时间'),
(N'posts', N'author_id', N'作者，引用 users.id，可为空'),
(N'posts', N'category_id', N'分类，引用 categories.id，可为空'),
(N'post_tags', NULL, N'文章与标签多对多关联'),
(N'post_tags', N'post_id', N'文章 id，引用 posts.id'),
(N'post_tags', N'tag_id', N'标签 id，引用 tags.id'),
(N'comments', NULL, N'评论；parent_id 非空表示回复；父评论删除需在应用层处理子评论'),
(N'comments', N'id', N'主键，自增'),
(N'comments', N'post_id', N'所属文章，引用 posts.id'),
(N'comments', N'parent_id', N'父评论 id；为空表示顶层评论；无外键级联删除'),
(N'comments', N'author_name', N'评论者显示名'),
(N'comments', N'content', N'评论正文'),
(N'comments', N'created_at', N'发表时间');

DECLARE @t SYSNAME, @c SYSNAME, @v NVARCHAR(1000);

DECLARE desc_cur CURSOR LOCAL FAST_FORWARD FOR
SELECT t, c, v FROM @d ORDER BY t, c;

OPEN desc_cur;
FETCH NEXT FROM desc_cur INTO @t, @c, @v;

WHILE @@FETCH_STATUS = 0
BEGIN
    IF @c IS NULL
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM sys.extended_properties AS ep
            INNER JOIN sys.tables AS tb ON ep.major_id = tb.object_id
            INNER JOIN sys.schemas AS s ON tb.schema_id = s.schema_id
            WHERE s.name = N'dbo'
              AND tb.name = @t
              AND ep.name = N'MS_Description'
              AND ep.minor_id = 0
        )
            EXEC sys.sp_updateextendedproperty
                @name = N'MS_Description',
                @value = @v,
                @level0type = N'SCHEMA',
                @level0name = N'dbo',
                @level1type = N'TABLE',
                @level1name = @t;
        ELSE
            EXEC sys.sp_addextendedproperty
                @name = N'MS_Description',
                @value = @v,
                @level0type = N'SCHEMA',
                @level0name = N'dbo',
                @level1type = N'TABLE',
                @level1name = @t;
    END
    ELSE
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM sys.extended_properties AS ep
            INNER JOIN sys.columns AS col ON ep.major_id = col.object_id AND ep.minor_id = col.column_id
            INNER JOIN sys.tables AS tb ON col.object_id = tb.object_id
            INNER JOIN sys.schemas AS s ON tb.schema_id = s.schema_id
            WHERE s.name = N'dbo'
              AND tb.name = @t
              AND col.name = @c
              AND ep.name = N'MS_Description'
        )
            EXEC sys.sp_updateextendedproperty
                @name = N'MS_Description',
                @value = @v,
                @level0type = N'SCHEMA',
                @level0name = N'dbo',
                @level1type = N'TABLE',
                @level1name = @t,
                @level2type = N'COLUMN',
                @level2name = @c;
        ELSE
            EXEC sys.sp_addextendedproperty
                @name = N'MS_Description',
                @value = @v,
                @level0type = N'SCHEMA',
                @level0name = N'dbo',
                @level1type = N'TABLE',
                @level1name = @t,
                @level2type = N'COLUMN',
                @level2name = @c;
    END;

    FETCH NEXT FROM desc_cur INTO @t, @c, @v;
END;

CLOSE desc_cur;
DEALLOCATE desc_cur;

PRINT N'BlogDB 表结构检查完毕；MS_Description 已写入或更新。';
GO
