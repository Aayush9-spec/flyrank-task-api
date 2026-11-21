-- 1. Overall summary
SELECT
    COUNT(*) AS total_books,
    ROUND(AVG(price), 2) AS average_price,
    ROUND(MIN(price), 2) AS minimum_price,
    ROUND(MAX(price), 2) AS maximum_price,
    ROUND(AVG(rating), 2) AS average_rating
FROM books;

-- 2. Rating distribution
SELECT
    rating,
    COUNT(*) AS book_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM books), 1) AS percentage
FROM books
GROUP BY rating
ORDER BY rating;

-- 3. Top 10 most expensive books
SELECT title, price, rating, url
FROM books
ORDER BY price DESC, title ASC
LIMIT 10;

-- 4. Price bands
SELECT
    CASE
        WHEN price < 20 THEN 'Under £20'
        WHEN price < 30 THEN '£20–£29.99'
        WHEN price < 40 THEN '£30–£39.99'
        WHEN price < 50 THEN '£40–£49.99'
        ELSE '£50 and above'
    END AS price_band,
    COUNT(*) AS book_count,
    ROUND(AVG(price), 2) AS average_price
FROM books
GROUP BY price_band
ORDER BY MIN(price);
