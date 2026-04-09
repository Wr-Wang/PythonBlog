/*
  BlogDB 数据库创建（SQL Server）
  --------------------------------
  与 backend/.env 中 DATABASE_URL 指向的实例一致时使用。

  推荐在 SSMS 中按顺序执行：
  1) 本文件：创建数据库并切换到 BlogDB；
  2) tables_schema_with_descriptions.sql：建表、索引、外键及字段说明（MS_Description，可重复执行）。

  说明：博客 API 启动时仍会用 SQLAlchemy create_all 自动建缺失的表；
        本脚本便于 DBA 文档化、评审及在仅允许脚本建库的环境部署。
*/

IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = N'BlogDB')
    CREATE DATABASE BlogDB;
GO

USE BlogDB;
GO

/*
  下一步：同目录 tables_schema_with_descriptions.sql（建表 + 字段说明）。
*/
PRINT N'已切换到 BlogDB。请继续执行 tables_schema_with_descriptions.sql。';
GO
